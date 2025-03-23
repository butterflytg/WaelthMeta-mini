const app = getApp()

Page({
  data: {
    currentYear: new Date().getFullYear(),
    years: [],
    monthlyData: [],
    loading: true,
    empty: false,
    totalIncome: 0,
    totalExpense: 0,
    balance: 0,
    canvasContext: null,
    canvasNode: null
  },

  onLoad: function() {
    // 生成最近三年的年份选项
    const currentYear = new Date().getFullYear()
    const years = []
    for (let i = 0; i < 3; i++) {
      years.push(currentYear - i)
    }
    
    // 设置年份数据
    this.setData({
      years,
      currentYear: years[0]  // 确保使用years数组中的第一个年份
    }, () => {
      // 在设置完年份后初始化Canvas
      this.initCanvas()
    })
  },

  // 初始化Canvas
  async initCanvas() {
    const query = wx.createSelectorQuery()
    query.select('#chartCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (res[0]) {
          const canvas = res[0].node
          const ctx = canvas.getContext('2d')
          
          // 设置canvas大小
          const dpr = wx.getSystemInfoSync().pixelRatio
          canvas.width = res[0].width * dpr
          canvas.height = res[0].height * dpr
          ctx.scale(dpr, dpr)

          this.setData({
            canvasContext: ctx,
            canvasNode: canvas
          }, () => {
            // Canvas初始化完成后加载数据
            this.loadMonthlyData()
          })
        } else {
          console.error('Canvas node not found')
          // 即使Canvas初始化失败也加载数据
          this.loadMonthlyData()
        }
      })
  },

  // 年份选择器变化处理
  onYearChange: function(e) {
    const index = e.detail.value
    const year = this.data.years[index]
    console.log('切换年份:', year)  // 添加日志
    
    this.setData({
      currentYear: year,
      loading: true,
      monthlyData: [],  // 清空旧数据
      totalIncome: 0,   // 重置总收入
      totalExpense: 0,  // 重置总支出
      balance: 0        // 重置结余
    }, () => {
      // 在设置完年份后立即加载数据
      this.loadMonthlyData()
    })
  },

  // 加载月度数据
  loadMonthlyData: function() {
    const that = this
    console.log('正在加载年份数据:', this.data.currentYear)  // 添加日志
    
    // 显示加载状态
    this.setData({ loading: true, empty: false })

    wx.request({
      url: `${app.globalData.baseUrl}/api/monthly_stats`,
      method: 'GET',
      data: {
        year: this.data.currentYear
      },
      success: function(res) {
        console.log('API返回数据:', res.data)  // 添加日志
        if (res.data.code === 0) {
          const monthlyData = res.data.data || []
          let totalIncome = 0
          let totalExpense = 0

          // 计算年度总计
          monthlyData.forEach(item => {
            totalIncome += Number(item.income) || 0
            totalExpense += Number(item.expense) || 0
          })

          // 检查是否有任何收入或支出
          const hasData = monthlyData.some(item => 
            (Number(item.income) > 0 || Number(item.expense) > 0)
          )

          that.setData({
            monthlyData,
            totalIncome: totalIncome.toFixed(2),
            totalExpense: totalExpense.toFixed(2),
            balance: (totalIncome - totalExpense).toFixed(2),
            loading: false,
            empty: !hasData
          }, () => {
            // 在数据更新完成后绘制图表
            if (hasData) {
              console.log('开始绘制图表')  // 添加日志
              that.drawChart()
            } else {
              console.log('没有数据，不绘制图表')  // 添加日志
              // 清空画布
              if (that.data.canvasContext && that.data.canvasNode) {
                const ctx = that.data.canvasContext
                const canvas = that.data.canvasNode
                const width = canvas.width / wx.getSystemInfoSync().pixelRatio
                const height = canvas.height / wx.getSystemInfoSync().pixelRatio
                ctx.clearRect(0, 0, width, height)
              }
            }
          })
        } else {
          console.error('API请求失败:', res.data)  // 添加日志
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          })
          that.setData({
            loading: false,
            empty: true
          })
        }
      },
      fail: function(error) {
        console.error('网络请求失败:', error)  // 添加日志
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        })
        that.setData({
          loading: false,
          empty: true
        })
      }
    })
  },

  // 绘制图表
  drawChart: function() {
    const ctx = this.data.canvasContext
    const canvas = this.data.canvasNode
    if (!ctx || !canvas) {
      console.error('Canvas context or node not available')
      return
    }

    const width = canvas.width / wx.getSystemInfoSync().pixelRatio
    const height = canvas.height / wx.getSystemInfoSync().pixelRatio
    const padding = 40
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2

    // 清空画布
    ctx.clearRect(0, 0, width, height)

    // 找出最大值用于计算比例
    const maxValue = Math.max(
      ...this.data.monthlyData.map(item => Math.max(Number(item.income) || 0, Number(item.expense) || 0))
    )
    
    // 如果没有数据，直接返回
    if (maxValue === 0) {
      this.setData({ empty: true })
      return
    }

    // 绘制坐标轴
    ctx.beginPath()
    ctx.strokeStyle = '#ddd'
    ctx.lineWidth = 1

    // X轴
    ctx.moveTo(padding, height - padding)
    ctx.lineTo(width - padding, height - padding)

    // Y轴
    ctx.moveTo(padding, height - padding)
    ctx.lineTo(padding, padding)
    ctx.stroke()

    // 绘制刻度
    ctx.fillStyle = '#666'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'

    // X轴刻度（月份）
    for (let i = 0; i < 12; i++) {
      const x = padding + (chartWidth * i / 11)
      ctx.fillText((i + 1) + '月', x, height - padding + 20)
    }

    // Y轴刻度
    const yStep = maxValue / 5
    for (let i = 0; i <= 5; i++) {
      const y = height - padding - (chartHeight * i / 5)
      const value = (yStep * i).toFixed(0)
      ctx.textAlign = 'right'
      ctx.fillText(value, padding - 5, y + 4)
    }

    // 绘制柱状图
    const barWidth = (chartWidth / 12) * 0.3  // 每个月的柱子宽度
    const barGap = barWidth * 0.5  // 两个柱子之间的间隔

    this.data.monthlyData.forEach((item, index) => {
      const x = padding + (chartWidth * index / 11)
      const income = Number(item.income) || 0
      const expense = Number(item.expense) || 0

      // 收入柱子
      const incomeHeight = (income / maxValue) * chartHeight
      ctx.fillStyle = '#4CAF50'
      ctx.fillRect(
        x - barWidth - barGap,
        height - padding - incomeHeight,
        barWidth,
        incomeHeight
      )

      // 支出柱子
      const expenseHeight = (expense / maxValue) * chartHeight
      ctx.fillStyle = '#F44336'
      ctx.fillRect(
        x + barGap,
        height - padding - expenseHeight,
        barWidth,
        expenseHeight
      )

      // 显示数值
      ctx.fillStyle = '#333'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'
      if (income > 0) {
        ctx.fillText(income.toFixed(0), x - barWidth - barGap + barWidth/2, height - padding - incomeHeight - 5)
      }
      if (expense > 0) {
        ctx.fillText(expense.toFixed(0), x + barGap + barWidth/2, height - padding - expenseHeight - 5)
      }
    })
  }
}) 
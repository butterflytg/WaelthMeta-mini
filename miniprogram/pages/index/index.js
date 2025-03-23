const { request } = require('../../utils/request')

Page({
  data: {
    messages: [],
    inputValue: '',
    styles: ['轻松', '幽默', '正式'],
    styleIndex: 0,
    scrollToMessage: '',
    user_name: '',
    isLoading: false
  },

  onLoad() {
    // 页面加载时执行
  },

  onInput(e) {
    this.setData({
      inputValue: e.detail.value
    })
  },

  onStyleChange(e) {
    this.setData({
      styleIndex: e.detail.value
    })
  },

  async sendMessage() {
    if (!this.data.inputValue.trim()) return
    if (this.data.isLoading) return

    const message = this.data.inputValue
    this.setData({
      inputValue: '',
      messages: [...this.data.messages, { type: 'user', content: message }],
      isLoading: true
    })

    try {
      const response = await request({
        url: '/api/chat',
        method: 'POST',
        data: {
          message,
          style: this.data.styles[this.data.styleIndex],
          user_name: this.data.user_name
        }
      })

      this.setData({
        messages: [...this.data.messages, { type: 'assistant', content: response.message }],
        user_name: response.user_name
      })
    } catch (error) {
      console.error('发送消息失败:', error)
      wx.showToast({
        title: error.message || '发送失败，请重试',
        icon: 'none',
        duration: 2000
      })
    } finally {
      this.setData({
        isLoading: false
      })
    }

    // 滚动到最新消息
    this.setData({
      scrollToMessage: `msg-${this.data.messages.length - 1}`
    })
  }
}) 
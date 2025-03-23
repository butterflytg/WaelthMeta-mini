const app = getApp()

const request = (options) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'content-type': 'application/json',
        ...options.header
      },
      timeout: 30000, // 增加超时时间到30秒
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          console.error('请求失败:', res)
          reject(new Error(`请求失败: ${res.statusCode}`))
        }
      },
      fail: (err) => {
        console.error('请求错误:', err)
        if (err.errMsg.includes('timeout')) {
          reject(new Error('请求超时，请检查网络连接'))
        } else {
          reject(new Error('网络请求失败，请稍后重试'))
        }
      }
    })
  })
}

module.exports = {
  request
} 
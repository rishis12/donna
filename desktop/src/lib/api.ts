const API_BASE = 'http://localhost:8000'

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
  }

  private async request(method: string, path: string, body?: any) {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || 'Request failed')
    }

    return response.json()
  }

  get(path: string) {
    return this.request('GET', path)
  }

  post(path: string, body?: any) {
    return this.request('POST', path, body)
  }

  patch(path: string, body?: any) {
    return this.request('PATCH', path, body)
  }

  delete(path: string) {
    return this.request('DELETE', path)
  }

  async uploadAudio(path: string, audioBlob: Blob) {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    formData.append('current_time', new Date().toISOString())

    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: formData
    })

    if (!response.ok) {
      throw new Error('Failed to upload audio')
    }

    return response.json()
  }
}

export const api = new ApiClient()


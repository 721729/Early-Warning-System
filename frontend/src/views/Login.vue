<template>
  <div class="login-wrapper">
    <div class="login-box">
      <h1>⚡ 绿电哨兵</h1>
      <p class="subtitle">焚烧炉设备健康度监测平台</p>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>工号</label>
          <input v-model="form.username" type="text" placeholder="输入工号" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="输入密码" autocomplete="current-password" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>
      <p class="footer">Demo 账号: admin / admin123</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '../api/request'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

// -------- 输入清洗: 去除前后空格, 过滤特殊字符 --------
function sanitize(str) {
  return str.trim().replace(/[<>"';&]/g, '')
}

async function handleLogin() {
  error.value = ''
  const uname = sanitize(form.username)
  const pwd = form.password   // 密码不过滤特殊字符

  if (!uname || !pwd) {
    error.value = '工号和密码不能为空'
    return
  }
  if (uname.length > 32) {
    error.value = '工号格式错误'
    return
  }

  loading.value = true
  try {
    const res = await authAPI.login({ username: uname, password: pwd })
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    localStorage.setItem('user_info', JSON.stringify(res.data.user))
    router.push('/')
  } catch (e) {
    if (e.response?.status === 401) {
      error.value = '工号或密码错误'
    } else if (e.response?.status === 429) {
      error.value = '登录尝试过多，请稍后再试'
    } else {
      error.value = '服务器连接失败，请检查网络'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
}
.login-box {
  background: #1a2a3a; border-radius: 12px; padding: 40px;
  width: 380px; max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
h1 { text-align: center; font-size: 26px; color: #4fc3f7; margin-bottom: 4px; }
.subtitle { text-align: center; font-size: 13px; color: #78909c; margin-bottom: 28px; }
.field { margin-bottom: 18px; }
.field label { display: block; font-size: 13px; color: #b0bec5; margin-bottom: 6px; }
.field input {
  width: 100%; padding: 10px 14px; border-radius: 6px;
  border: 1px solid #37474f; background: #253548; color: #e0e0e0;
  font-size: 14px; outline: none; transition: border .2s;
}
.field input:focus { border-color: #4fc3f7; }
.error { color: #ef5350; font-size: 13px; margin-bottom: 12px; }
button {
  width: 100%; padding: 12px; border: none; border-radius: 6px;
  background: #1976d2; color: #fff; font-size: 15px; cursor: pointer;
  transition: background .2s;
}
button:hover { background: #1565c0; }
button:disabled { background: #37474f; cursor: not-allowed; }
.footer { text-align: center; font-size: 12px; color: #546e7a; margin-top: 20px; }
</style>

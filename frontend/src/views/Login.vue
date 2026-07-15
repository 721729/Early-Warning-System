<template>
  <div class="wrap">
    <div class="box">
      <div class="icon">⚡</div>
      <h1>绿电哨兵</h1>
      <p>焚烧炉设备健康度监测平台</p>
      <form @submit.prevent="login" autocomplete="off">
        <input type="text" name="fakeuser" style="display:none" />
        <input type="password" name="fakepass" style="display:none" />
        <input v-model="f.username" type="text" placeholder="工号" name="uid" autocomplete="new-password" />
        <input v-model="f.password" type="password" placeholder="密码" name="pwd" autocomplete="new-password" />
        <p v-if="err" class="err">{{ err }}</p>
        <button type="submit" :disabled="ld">{{ ld ? '登录中...' : '登 录' }}</button>
      </form>
      <span class="hint">Demo: admin / admin123</span>
    </div>
  </div>
</template>
<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '../api/request'
const r = useRouter()
const f = reactive({ username: '', password: '' })
const ld = ref(false), err = ref('')
onMounted(() => { f.username = ''; f.password = '' })
async function login() {
  err.value = ''
  if (!f.username.trim() || !f.password) { err.value = '工号和密码不能为空'; return }
  ld.value = true
  try {
    const res = await authAPI.login({ username: f.username.trim(), password: f.password })
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    localStorage.setItem('user_info', JSON.stringify(res.data.user))
    r.push('/')
  } catch (e) {
    err.value = e.response?.status === 401 ? '工号或密码错误' : '服务器连接失败'
  } finally { ld.value = false }
}
</script>
<style scoped>
.wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: radial-gradient(ellipse at top, #0d1b2a 0%, #0a0e17 70%); }
.box { background: rgba(17,24,39,.9); border: 1px solid #1e2d3d; border-radius: 16px; padding: 48px 40px; width: 380px; max-width: 90vw; text-align: center; backdrop-filter: blur(10px); }
.icon { font-size: 48px; margin-bottom: 8px; }
h1 { font-size: 26px; color: #00e5ff; font-weight: 700; letter-spacing: 2px; }
p { font-size: 13px; color: #546e7a; margin: 6px 0 28px; }
input { width: 100%; padding: 12px 16px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #1e2d3d; background: #0a0e17; color: #ccd6f6; font-size: 14px; outline: none; transition: border .2s; }
input:focus { border-color: #00e5ff; }
.err { color: #ff5252; font-size: 12px; margin-bottom: 8px; }
button { width: 100%; padding: 12px; border: none; border-radius: 8px; background: linear-gradient(135deg, #00695c, #00838f); color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; letter-spacing: 2px; transition: opacity .2s; }
button:hover { opacity: .85; }
button:disabled { opacity: .4; cursor: not-allowed; }
.hint { font-size: 11px; color: #37474f; margin-top: 16px; display: block; }
</style>

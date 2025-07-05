<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Bejelentkezés
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Autokmdb login
        </p>
      </div>
      <form class="mt-8 space-y-6" @submit.prevent="handleLogin">
        <div class="rounded-md shadow-sm -space-y-px">
          <div>
            <label for="username" class="sr-only">Felhasználónév</label>
            <UInput
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              placeholder="Felhasználónév"
              class="mb-4"
              :disabled="loading"
            />
          </div>
          <div>
            <label for="password" class="sr-only">Jelszó</label>
            <UInput
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              placeholder="Jelszó"
              :disabled="loading"
            />
          </div>
        </div>

        <div v-if="error" class="text-red-600 text-sm text-center">
          {{ error }}
        </div>

        <div>
          <UButton
            type="submit"
            :loading="loading"
            :disabled="loading"
            class="w-full"
            size="lg"
          >
            Bejelentkezés
          </UButton>
        </div>

        <div class="text-center">
          <a 
            :href="config.public.adminUrl" 
            target="_blank" 
            class="text-blue-600 hover:text-blue-500"
          >
            Bejelentkezés az admin felületen
          </a>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">

const emit = defineEmits(['loginSuccess']);

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;

const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function handleLogin() {
  loading.value = true;
  error.value = '';
  
  try {
    const response = await $fetch(baseUrl + "/api/login", {
      method: "POST",
      body: {
        username: username.value,
        password: password.value
      },
      credentials: 'include'
    });
    
    if (response.success) {
      emit('loginSuccess');
      console.log('Bejelentkezés sikeres');
    } else {
      error.value = 'Bejelentkezési hiba történt';
    }
  } catch (err) {
    if (err.status === 401) {
      error.value = 'Hibás felhasználónév vagy jelszó';
    } else {
      error.value = 'Bejelentkezési hiba történt';
    }
  } finally {
    loading.value = false;
  }
}
</script>

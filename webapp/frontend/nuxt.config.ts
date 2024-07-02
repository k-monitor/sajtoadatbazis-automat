// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxt/ui'],
  ssr: false,
  runtimeConfig: {
    public: {
      baseUrl: process.env.BASE_URL
    }
  }
})

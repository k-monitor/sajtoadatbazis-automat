// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxt/ui', "@nuxt/icon"],
  ssr: false,
  runtimeConfig: {
    public: {
      baseUrl: process.env.BASE_URL,
      adminUrl: process.env.ADMIN_URL,
    }
  }
})
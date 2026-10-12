<script setup lang="ts">
import { $authFetch } from "~/auth_fetch";

const props = defineProps<{
  isOpen: boolean;
  status: any;
}>();

const emit = defineEmits<{
  (e: "update:isOpen", value: boolean): void;
  (e: "update:status", status: any): void;
  (e: "error", error: any): void;
}>();

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;
const toast = useToast();

// Set once the sign-in page is opened, then the address of the callback page is pasted back.
const authorizeUrl = ref<string | null>(null);
const callbackUrl = ref("");
const loginError = ref<string | null>(null);
const busy = ref<string | null>(null);
const justConnected = ref(false);

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      authorizeUrl.value = null;
      callbackUrl.value = "";
      loginError.value = null;
      justConnected.value = false;
    }
  }
);

function close() {
  emit("update:isOpen", false);
}

function formatTime(seconds: number): string {
  return new Date(seconds * 1000).toLocaleString("hu-HU");
}

async function startLogin(newAccount: boolean) {
  busy.value = newAccount ? "new" : "login";
  try {
    const response: any = await $authFetch(baseUrl + "/api/chatgpt/login", {
      method: "POST",
      body: { new_account: newAccount },
    });
    authorizeUrl.value = response.url;
    loginError.value = null;
    window.open(response.url, "_blank", "noopener");
  } catch (error) {
    emit("error", error);
  } finally {
    busy.value = null;
  }
}

async function finishLogin() {
  busy.value = "callback";
  try {
    const status = await $authFetch(baseUrl + "/api/chatgpt/callback", {
      method: "POST",
      body: { url: callbackUrl.value },
    });
    emit("update:status", status);
    authorizeUrl.value = null;
    callbackUrl.value = "";
    loginError.value = null;
    justConnected.value = true;
  } catch (error: any) {
    // Shown here, as the user may have to paste again or start over.
    if (error?.status === 400) loginError.value = error.data?.error;
    else emit("error", error);
  } finally {
    busy.value = null;
  }
}

async function logout() {
  busy.value = "logout";
  try {
    const response: any = await $authFetch(baseUrl + "/api/chatgpt/logout", { method: "POST" });
    emit("update:status", response);
    if (!response.revoked) {
      toast.add({
        title: "Nem sikerült megerősíteni a leválasztást",
        description: "A tokeneket töröltük, de az alkalmazást a ChatGPT beállításaiban is leválaszthatod.",
        color: "amber",
        timeout: 0,
      });
    }
  } catch (error) {
    emit("error", error);
  } finally {
    busy.value = null;
  }
}
</script>

<template>
  <UModal :model-value="isOpen" @update:model-value="emit('update:isOpen', $event)" :ui="{ width: 'sm:max-w-xl' }">
    <div v-if="status" class="p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">ChatGPT-előfizetés</h2>
        <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="close" />
      </div>

      <template v-if="justConnected && status.plan_usage">
        <p class="font-semibold">A ChatGPT-előfizetésedet használod</p>
        <p class="text-sm text-gray-600 mt-2">
          A leírások generálása mostantól a(z) {{ status.email }} fiók ChatGPT-előfizetésének keretéből fogy,
          nem API-díjként, akárki indítja a webappban. A használatot és az alkalmazásnak szánt keretet a ChatGPT
          beállításaiban kezelheted.
        </p>
        <div class="flex justify-end gap-2 mt-4">
          <UButton color="gray" variant="outline" :to="status.usage_url" target="_blank">Használat kezelése</UButton>
          <UButton @click="close">Rendben</UButton>
        </div>
      </template>

      <template v-else-if="status.connected">
        <p class="text-sm">
          Bejelentkezve: <span class="font-semibold">{{ status.name || status.email }}</span>
          <template v-if="status.name"> ({{ status.email }})</template>
        </p>

        <UAlert v-if="!status.plan_usage" class="mt-3" color="amber" variant="soft"
          title="Az előfizetés használata nincs engedélyezve"
          description="Jelentkezz be újra, és engedélyezd a ChatGPT-előfizetésed használatát ennek az alkalmazásnak. Addig a leírások a sorban várakoznak." />
        <template v-else>
          <p class="text-sm text-green-700 mt-2">ChatGPT-előfizetés használatban</p>
          <p class="text-sm text-gray-600 mt-2">
            Modell: <span class="font-mono">{{ status.model || "?" }}</span>,
            webes keresés: {{ status.web_search ? "be" : "ki" }}
          </p>
          <p v-if="status.models?.length" class="text-xs text-gray-500 mt-1">
            Elérhető modellek: {{ status.models.map((m: any) => m.slug).join(", ") }}. Másikat a
            DESCRIPTION_CHATGPT_MODEL beállítással választhatsz.
          </p>
        </template>

        <UAlert v-if="status.problem" class="mt-3" color="amber" variant="soft"
          :title="'A generálás szünetel (' + formatTime(status.problem.time) + ')'"
          :description="status.problem.message" />

        <div class="flex justify-end gap-2 mt-4">
          <UButton color="gray" variant="outline" :to="status.usage_url" target="_blank">Használat kezelése</UButton>
          <UButton v-if="!status.plan_usage" :loading="busy === 'login'" @click="startLogin(false)">
            Bejelentkezés újra
          </UButton>
          <UButton color="red" variant="outline" :loading="busy === 'logout'" @click="logout">Leválasztás</UButton>
        </div>
      </template>

      <template v-else>
        <p class="text-sm text-gray-600">
          A leírásokat a webapp egy erre jogosult ChatGPT-előfizetés keretéből generálja, API-kulcs helyett. A
          csatlakoztatott fiók előfizetése fogy minden felhasználó kérésénél. Amíg nincs csatlakoztatott fiók, a
          leírások a sorban várakoznak.
        </p>

        <UAlert v-if="status.problem" class="mt-3" color="amber" variant="soft" :description="status.problem.message" />

        <div class="flex items-center gap-2 mt-4 flex-wrap">
          <UButton :loading="busy === 'login'" @click="startLogin(false)">Folytatás ChatGPT-vel</UButton>
          <template v-if="status.registered">
            <span class="text-sm text-gray-500">{{ status.email }}</span>
            <UButton color="gray" variant="ghost" size="sm" :loading="busy === 'new'" @click="startLogin(true)">
              Másik fiókkal
            </UButton>
          </template>
        </div>

        <div v-if="authorizeUrl" class="mt-4">
          <p class="text-sm text-gray-600">
            A bejelentkezés után a böngésző egy nem betöltődő oldalra ugrik (http://127.0.0.1:1455/auth/callback?...),
            ez így rendben van. Másold be ide annak az oldalnak a teljes címét a címsorból!
            <a :href="authorizeUrl" target="_blank" rel="noopener" class="underline">Ha nem nyílt meg az új lap,
              kattints ide.</a>
          </p>
          <div class="flex gap-2 mt-2">
            <UInput v-model="callbackUrl" class="flex-grow" placeholder="http://127.0.0.1:1455/auth/callback?code=..."
              @keyup.enter="callbackUrl && finishLogin()" />
            <UButton :disabled="!callbackUrl" :loading="busy === 'callback'" @click="finishLogin">Befejezés</UButton>
          </div>
        </div>

        <UAlert v-if="loginError" class="mt-3" color="red" variant="soft" :description="loginError" />
      </template>
    </div>
  </UModal>
</template>

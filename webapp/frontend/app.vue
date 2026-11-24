<template>
  <div>
    <NuxtPage />
    <UNotifications />
  </div>
</template>

<script setup lang="ts">
const toast = useToast();

onMounted(() => {
  try {
    const raw = sessionStorage.getItem("pendingToast");
    if (!raw) return;
    sessionStorage.removeItem("pendingToast");
    const data = JSON.parse(raw);
    toast.add(data);
  } catch {
    sessionStorage.removeItem("pendingToast");
  }
});
</script>

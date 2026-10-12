<script setup lang="ts">
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";

const props = defineProps<{
  modelValue: string;
  editable: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

// Only the formatting that the backend keeps when it sanitizes the HTML for the KMDB.
const editor = useEditor({
  content: props.modelValue,
  editable: props.editable,
  extensions: [
    StarterKit.configure({
      heading: false,
      blockquote: false,
      code: false,
      codeBlock: false,
      horizontalRule: false,
      trailingNode: false,
      link: { openOnClick: false, defaultProtocol: "https" },
    }),
  ],
  // The editor normalizes the HTML (e.g. adds target="_blank" to the links), what it shows is saved.
  onCreate: ({ editor }) => emit("update:modelValue", editor.getHTML()),
  onUpdate: ({ editor }) => emit("update:modelValue", editor.getHTML()),
});

watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && value !== editor.value.getHTML()) {
      editor.value.commands.setContent(value, { emitUpdate: false });
    }
  }
);
watch(
  () => props.editable,
  (value) => editor.value?.setEditable(value)
);

function setLink() {
  const url = window.prompt("Link URL-je (üresen hagyva törlődik):", editor.value?.getAttributes("link").href ?? "");
  if (url === null) return;
  const chain = editor.value!.chain().focus().extendMarkRange("link");
  (url.trim() ? chain.setLink({ href: url.trim() }) : chain.unsetLink()).run();
}

const toolbar = computed(() => {
  const e = editor.value;
  if (!e) return [];
  return [
    { title: "Félkövér", icon: "i-mdi-format-bold", active: e.isActive("bold"), action: () => e.chain().focus().toggleBold().run() },
    { title: "Dőlt", icon: "i-mdi-format-italic", active: e.isActive("italic"), action: () => e.chain().focus().toggleItalic().run() },
    { title: "Aláhúzott", icon: "i-mdi-format-underline", active: e.isActive("underline"), action: () => e.chain().focus().toggleUnderline().run() },
    { title: "Felsorolás", icon: "i-mdi-format-list-bulleted", active: e.isActive("bulletList"), action: () => e.chain().focus().toggleBulletList().run() },
    { title: "Számozott lista", icon: "i-mdi-format-list-numbered", active: e.isActive("orderedList"), action: () => e.chain().focus().toggleOrderedList().run() },
    { title: "Link", icon: "i-mdi-link-variant", active: e.isActive("link"), action: setLink },
    { title: "Visszavonás", icon: "i-mdi-undo", active: false, action: () => e.chain().focus().undo().run() },
    { title: "Újra", icon: "i-mdi-redo", active: false, action: () => e.chain().focus().redo().run() },
  ];
});
</script>

<template>
  <div class="border border-gray-200 rounded" :class="editable ? '' : 'bg-gray-50'">
    <div v-if="editable" class="flex gap-0.5 p-1 border-b border-gray-200">
      <UButton v-for="button in toolbar" :key="button.title" :title="button.title" :icon="button.icon" size="xs"
        :color="button.active ? 'primary' : 'gray'" :variant="button.active ? 'soft' : 'ghost'" @click="button.action" />
    </div>
    <EditorContent :editor="editor" class="description-editor overflow-y-auto"
      :class="editable ? 'h-[28rem]' : 'max-h-[32rem]'" />
  </div>
</template>

<style scoped>
/* Tailwind's reset removes the spacing and markers that the KMDB site shows. */
.description-editor :deep(.ProseMirror) {
  padding: 0.75rem;
  outline: none;
  min-height: 100%;
}

.description-editor :deep(p) {
  margin-bottom: 0.75rem;
}

.description-editor :deep(ul) {
  list-style: disc;
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.description-editor :deep(ol) {
  list-style: decimal;
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.description-editor :deep(a) {
  color: rgb(37 99 235);
  text-decoration: underline;
}
</style>

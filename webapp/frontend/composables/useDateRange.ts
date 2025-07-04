import { ref, computed, watch, type Ref } from 'vue'
import type { DataRow } from '../types'

export function useDateRange(data: Ref<DataRow[]>) {
  const startDate = ref('')
  const endDate = ref('')
  const startDateIndex = ref(0)
  const endDateIndex = ref(0)

  watch(data, (newData) => {
    if (newData.length > 0) {
      startDate.value = newData[0].date
      startDateIndex.value = 0
      endDate.value = newData[newData.length - 1].date
      endDateIndex.value = newData.length - 1
    }
  }, { immediate: true })

  const filteredData = computed(() => {
    if (data.value.length === 0) return []
    
    const start = Math.max(0, startDateIndex.value)
    const end = Math.min(data.value.length - 1, endDateIndex.value)
    
    return data.value.slice(start, end + 1)
  })

  const updateDateRange = () => {
    if (startDateIndex.value > endDateIndex.value) {
      const temp = startDateIndex.value
      startDateIndex.value = Number(endDateIndex.value)
      endDateIndex.value = Number(temp)
    }

    if (data.value.length > 0) {
      startDate.value = data.value[startDateIndex.value]?.date || ''
      endDate.value = data.value[endDateIndex.value]?.date || ''
    }
  }

  return {
    startDate,
    endDate,
    startDateIndex,
    endDateIndex,
    filteredData,
    updateDateRange,
  }
}
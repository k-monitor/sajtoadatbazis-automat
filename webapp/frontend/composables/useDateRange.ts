import { ref, computed } from 'vue'
import type { DataRow } from '../types'

export function useDateRange(data: Ref<DataRow[]>) {
  const startDate = ref('')
  const endDate = ref('')
  const startDateIndex = ref(0)
  const endDateIndex = ref(0)

watch(data, (newData) => {
    if (newData.length > 0) {
        endDate.value = newData[newData.length - 1].date
        endDateIndex.value = newData.length - 1
    }
}, { immediate: true })
  

  const filteredData = computed(() => {

    if (!endDate.value) return data.value

    return data.value.filter(
      (row) =>
        new Date(row.date) >= new Date(startDate.value) &&
        new Date(row.date) <= new Date(endDate.value)
    )
  })

  const updateDateRange = () => {
    if (startDateIndex.value > endDateIndex.value) {
      const temp = startDateIndex.value
      startDateIndex.value = Number(endDateIndex.value)
      endDateIndex.value = Number(temp)
    }

    startDate.value = data.value[startDateIndex.value]?.date
    endDate.value = data.value[endDateIndex.value]?.date
    
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
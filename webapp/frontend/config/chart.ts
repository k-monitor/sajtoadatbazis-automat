import { ChartOptions } from 'chart.js'

export const chartOptions: ChartOptions<'bar'> = {
  responsive: true,
  scales: {
    x: {
      stacked: true,
    },
    y: {
      stacked: true,
    },
  },
  elements: {
    bar: {
      borderRadius: {
        topLeft: 10,
        topRight: 10,
        bottomLeft: 0,
        bottomRight: 0,
      },
    },
  },
}

export const chartColors = {
  positive: {
    background: '#4CAF50',
    border: '#5EC16A',
  },
  todo: {
    background: '#4B84EE',
    border: '#4B84EE',
  },
  negative: {
    background: '#F44336',
    border: '#F44336',
  },
}
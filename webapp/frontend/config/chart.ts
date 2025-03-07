import { ChartOptions } from 'chart.js'

export const chartOptions: ChartOptions<'bar'> = {
  responsive: true,
  scales: {
    
    x: {
      bounds:'data',
      stacked: true,
      ticks: { color: 'black' },
      border: { color: 'black',width:2 }
    },
    y: {
      bounds:'data',
      stacked: true,
      ticks: { color: 'black' },
      border: { color: 'black',width:2 }
    },
  },
  elements: {
    bar: {
      borderRadius: {
        topLeft: 100,
        topRight: 100,
        bottomLeft: 0,
        bottomRight: 0,
      },
      
    },
  },
  plugins: {
    title: {
      display: true,
      text: 'Cikkek',
      color: 'black',
      align:'start'
    }
  }
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
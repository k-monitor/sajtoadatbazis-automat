export interface DataRow {
    date: string;
    count_positive: number;
    count_todo: number;
    count_negative: number;
  }
  
  export interface ChartColors {
    positive: {
      background: string;
      border: string;
    };
    todo: {
      background: string;
      border: string;
    };
    negative: {
      background: string;
      border: string;
    };
  }
  
  export interface DateRange {
    startDate: string;
    endDate: string;
    startIndex: number;
    endIndex: number;
  }
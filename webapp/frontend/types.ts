export interface DataRow {
    date: string;
    count_positive: number;
    count_todo: number;
    count_negative: number;
    count_negative_0: number;
    count_negative_1: number;
    count_negative_2: number;
    count_negative_3: number;
    count_negative_100: number;
    total_count: number;
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
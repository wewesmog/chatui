export interface Message {
  role: 'user' | 'assistant';
  content: string;
  formatted_message?: string;
  sources?: string[];
  follow_up_questions?: string[];
}

export interface Session {
  id: string;
  first_message: string;
  timestamp: string;
  messages: Message[];
  last_updated: string;
}

export interface GroupedSessions {
  today: Session[];
  thisWeek: Session[];
  thisMonth: Session[];
  older: Session[];
}

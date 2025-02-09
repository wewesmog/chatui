import { Session, GroupedSessions } from '@/types/chat';

const API_BASE_URL = 'http://localhost:8000';

class SessionError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = 'SessionError';
  }
}

export const sessionService = {
  async getSessions(): Promise<Session[]> {
    try {
      const userId = localStorage.getItem('nickname');
      if (!userId) {
        throw new SessionError('No user ID found');
      }

      const response = await fetch(`${API_BASE_URL}/api/chat-sessions?user_id=${encodeURIComponent(userId)}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new SessionError(
          'Failed to fetch sessions', 
          response.status
        );
      }
      const data = await response.json();
      return data.sessions || []; // Return empty array if no sessions
    } catch (error) {
      console.error('Error fetching sessions:', error);
      // Return empty array instead of throwing error for no sessions
      return [];
    }
  },

  async getSession(sessionId: string): Promise<Session | null> {
    try {
      const userId = localStorage.getItem('nickname');
      if (!userId) {
        throw new SessionError('No user ID found');
      }

      const response = await fetch(`${API_BASE_URL}/api/chat-sessions/${sessionId}?user_id=${encodeURIComponent(userId)}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new SessionError(
          'Failed to fetch session', 
          response.status
        );
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching session ${sessionId}:`, error);
      throw new SessionError(
        error instanceof SessionError 
          ? error.message 
          : 'Failed to load chat session'
      );
    }
  }
};

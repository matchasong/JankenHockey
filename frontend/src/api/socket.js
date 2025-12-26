import { WS_GAME_URL } from './endpoints';

export function createGameSocket({ onOpen, onMessage, onClose, onError, roomId, isRoomCreator }) {
  // Get authentication token
  const authToken = sessionStorage.getItem('authToken');
  if (!authToken) {
    throw new Error('Authentication token not found. Please login again.');
  }
  
  // Construct WebSocket URL with authentication token
  const url = `${WS_GAME_URL}?token=${encodeURIComponent(authToken)}&roomId=${roomId}&isRoomCreator=${isRoomCreator}`;
  const socket = new WebSocket(url);
  
  if (onOpen) socket.onopen = onOpen;
  if (onMessage) socket.onmessage = onMessage;
  if (onClose) socket.onclose = onClose;
  if (onError) socket.onerror = onError;
  return socket;
}

import { API_LIST_ROOMS, API_CREATE_ROOM, API_JOIN_ROOM } from './endpoints';

export async function fetchRooms() {
  const idToken = sessionStorage.getItem('idToken');
  const headers = {
    'Content-Type': 'application/json'
  };

  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const res = await fetch(API_LIST_ROOMS, {
    headers
  });
  const data = await res.json();
  return data.rooms || [];
}

export async function createRoom({ creatorName, message }) {
  const idToken = sessionStorage.getItem('idToken');
  const headers = {
    'Content-Type': 'application/json'
  };

  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const res = await fetch(API_CREATE_ROOM, {
    method: 'POST',
    headers,
    body: JSON.stringify({ creatorName, message })
  });
  if (!res.ok) throw new Error('Failed to create room');
  return await res.json();
}

export async function joinRoom(roomId, playerName) {
  const idToken = sessionStorage.getItem('idToken');
  const headers = {
    'Content-Type': 'application/json'
  };

  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const res = await fetch(API_JOIN_ROOM, {
    method: 'POST',
    headers,
    body: JSON.stringify({ roomId, playerName })
  });

  if (!res.ok) {
    if (res.status === 409) {
      // Handle room creator disconnected case
      const errorData = await res.json();
      if (errorData.code === 'CREATOR_DISCONNECTED') {
        throw new Error('CREATOR_DISCONNECTED');
      }
    }
    throw new Error('Failed to join room');
  }
  return await res.json();
}

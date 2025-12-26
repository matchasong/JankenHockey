import { API_SAVE_CPU_BATTLE_HISTORY, API_SAVE_GUEST_CPU_BATTLE_HISTORY } from './endpoints';

export async function saveCpuBattleHistory({ playerScore, cpuScore }) {
  const idToken = sessionStorage.getItem('idToken');
  
  if (!idToken) {
    throw new Error('Not authenticated');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${idToken}`
  };
  
  const res = await fetch(API_SAVE_CPU_BATTLE_HISTORY, {
    method: 'POST',
    headers,
    body: JSON.stringify({ 
      playerScore: playerScore,
      cpuScore: cpuScore 
    })
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(errorData.error || 'Failed to save CPU battle history');
  }
  
  return await res.json();
}

export async function saveGuestCpuBattleHistory({ playerScore, cpuScore }) {
  const headers = {
    'Content-Type': 'application/json'
  };
  
  const res = await fetch(API_SAVE_GUEST_CPU_BATTLE_HISTORY, {
    method: 'POST',
    headers,
    body: JSON.stringify({ 
      playerScore: playerScore,
      cpuScore: cpuScore 
    })
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(errorData.error || 'Failed to save guest CPU battle history');
  }
  
  return await res.json();
}

// Authentication utility functions
export function isAuthenticated() {
  const authToken = sessionStorage.getItem('authToken');
  const playerName = sessionStorage.getItem('playerName');
  return authToken && playerName && playerName.trim();
}

export function logout(router) {
  // Clear all authentication data
  sessionStorage.removeItem('authToken');
  sessionStorage.removeItem('idToken');
  sessionStorage.removeItem('playerName');
  sessionStorage.removeItem('username');

  // Redirect to login page
  router.push({ name: 'Login' });
}

export function getPlayerName() {
  return sessionStorage.getItem('playerName') || '';
}

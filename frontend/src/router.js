import { createRouter, createWebHistory } from 'vue-router'
import TopView from './TopView.vue'
import Game from './Game.vue'
import RoomList from './RoomList.vue'
import CreateRoom from './CreateRoom.vue'
import Login from './Login.vue'
import NotFound from './NotFound.vue'
import { isAuthenticated } from './utils/auth'

const routes = [
  { path: '/', component: TopView, name: 'TopView' },
  { path: '/login', component: Login, name: 'Login' },
  { 
    path: '/game', 
    component: Game, 
    name: 'Game',
    beforeEnter: (to, from, next) => {
      // Check if it's a CPU battle (no auth required)
      if (to.query.isCpuBattle === 'true' || to.query.cpu === 'true') {
        next(); // Allow CPU battles
        return;
      }
      
      // For regular multiplayer games, require authentication
      if (!isAuthenticated()) {
        next({ name: 'NotFound' }); // Redirect to 404 page
        return;
      }
      
      next(); // Allow authenticated access
    }
  },
  { 
    path: '/room', 
    component: RoomList, 
    name: 'RoomList',
    beforeEnter: (to, from, next) => {
      if (!isAuthenticated()) {
        next({ name: 'Login' });
        return;
      }
      next();
    }
  },
  { 
    path: '/room/create', 
    component: CreateRoom, 
    name: 'CreateRoom',
    beforeEnter: (to, from, next) => {
      if (!isAuthenticated()) {
        next({ name: 'Login' });
        return;
      }
      next();
    }
  },
  { path: '/404', component: NotFound, name: 'NotFound' },
  { path: '/:pathMatch(.*)*', component: NotFound, name: 'CatchAll' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

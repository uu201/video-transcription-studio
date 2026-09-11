import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Workspace',
    component: () => import('@/views/Workspace.vue'),
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        name: 'Overview',
        component: () => import('@/views/Overview.vue')
      },
      {
        path: 'sources',
        name: 'Sources',
        component: () => import('@/views/Sources.vue')
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue')
      },
      {
        path: 'tasks/:id',
        name: 'TaskDetail',
        component: () => import('@/views/TaskDetail.vue')
      },
      {
        path: 'results',
        name: 'Results',
        component: () => import('@/views/Results.vue')
      },
      {
        path: 'results/:id',
        name: 'ResultDetail',
        component: () => import('@/views/TaskDetail.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

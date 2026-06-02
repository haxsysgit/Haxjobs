import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import HomeView from './HomeView.vue'

describe('HomeView', () => {
  it('shows a connected dashboard summary from the HaxJobs API', async () => {
    const fetchMock = vi.fn((url) => {
      if (url === 'http://localhost:8000/health') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'ok', service: 'haxjobs-api' }),
        })
      }

      if (url === 'http://localhost:8000/api/jobs') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              { id: 'job-1', company: 'ExampleCo', title: 'Backend Engineer', status: 'saved' },
            ]),
        })
      }

      if (url === 'http://localhost:8000/api/profiles') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: 'profile-1', full_name: 'Arinze Elenasulu' }]),
        })
      }

      if (url === 'http://localhost:8000/api/hermes-tasks') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: 'task-1', task_type: 'analyze_job', status: 'pending' }]),
        })
      }

      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('1 saved job')
      expect(wrapper.text()).toContain('1 profile')
      expect(wrapper.text()).toContain('1 Hermes task')
      expect(wrapper.text()).toContain('ExampleCo')
      expect(wrapper.text()).toContain('Backend Engineer')
    })
  })
})

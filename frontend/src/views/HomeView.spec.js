import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import HomeView from './HomeView.vue'

describe('HomeView', () => {
  it('shows a connected dashboard summary from the HaxJobs API', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: 'ok', service: 'haxjobs-api' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([{ id: 'job-1', title: 'Backend Engineer', company: 'ExampleCo', status: 'saved' }]),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([{ id: 'profile-1', full_name: 'Arinze' }]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([{ id: 'task-1', task_type: 'analyze_job' }]) })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('haxjobs-api is online')
      expect(wrapper.text()).toContain('ExampleCo')
      expect(wrapper.text()).toContain('1 saved job')
      expect(wrapper.text()).toContain('1 profile')
      expect(wrapper.text()).toContain('1 Hermes task')
    })
  })

  it('renders a future Hermes pipeline map for upcoming workflow stages', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([]) }),
    )

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Live pipeline map')
      expect(wrapper.text()).toContain('Capture')
      expect(wrapper.text()).toContain('Analyze')
      expect(wrapper.text()).toContain('Generate pack')
      expect(wrapper.text()).toContain('Review')
      expect(wrapper.text()).toContain('Outreach')
    })
  })
})

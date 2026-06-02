import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import HomeView from './HomeView.vue'

describe('HomeView', () => {
  it('shows the backend health status from the HaxJobs API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', service: 'haxjobs-api' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(HomeView)
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('haxjobs-api is online')
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/health')
  })
})

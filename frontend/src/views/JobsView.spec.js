import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import JobsView from './JobsView.vue'

describe('JobsView', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads saved jobs and lets the user save a new manual job from the UI', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'job-1',
            company: 'ExampleCo',
            title: 'Backend Engineer',
            status: 'saved',
            application: { id: 'app-1', status: 'Saved' },
          }),
      })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(JobsView)

    await vi.waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/jobs', {})
    })

    await wrapper.get('[data-test="company-input"]').setValue('ExampleCo')
    await wrapper.get('[data-test="title-input"]').setValue('Backend Engineer')
    await wrapper.get('[data-test="source-platform-input"]').setValue('manual')
    await wrapper.get('[data-test="job-form"]').trigger('submit.prevent')

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('ExampleCo')
      expect(wrapper.text()).toContain('Backend Engineer')
      expect(wrapper.text()).toContain('Saved')
    })

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/api/jobs/manual',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})

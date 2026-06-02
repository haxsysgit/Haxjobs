import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfilesView from './ProfilesView.vue'

describe('ProfilesView', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows stored profiles and explains the private local profile import path', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([{ id: 'profile-1', full_name: 'Arinze Elenasulu', preferred_roles: ['Backend Engineer'] }]),
    })

    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(ProfilesView)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Arinze Elenasulu')
      expect(wrapper.text()).toContain('Backend Engineer')
      expect(wrapper.text()).toContain('data/private/arinze_profile.local.json')
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/profiles', {})
  })
})

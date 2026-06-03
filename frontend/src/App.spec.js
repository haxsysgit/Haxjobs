import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import App from './App.vue'

describe('App shell', () => {
  it('toggles between dark and light cockpit themes', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem')
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')

    const wrapper = mount(App, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
          RouterView: true,
          'router-link': RouterLinkStub,
          'router-view': true,
        },
      },
    })

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(wrapper.text()).toContain('Dark cockpit')

    await wrapper.get('[data-test="theme-toggle"]').trigger('click')

    expect(document.documentElement.dataset.theme).toBe('light')
    expect(wrapper.text()).toContain('Light cockpit')
    expect(setItem).toHaveBeenCalledWith('haxjobs-theme', 'light')
  })

  it('surfaces future Hermes workflow affordances in the shell', () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
          RouterView: true,
          'router-link': RouterLinkStub,
          'router-view': true,
        },
      },
    })

    expect(wrapper.text()).toContain('Command Dock')
    expect(wrapper.text()).toContain('Analyze')
    expect(wrapper.text()).toContain('Pack')
    expect(wrapper.text()).toContain('Outreach')
    expect(wrapper.text()).toContain('Apply assist')
  })
})

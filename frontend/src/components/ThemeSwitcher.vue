<template>
  <div>
    <Button
      label="Customize Theme"
      icon="pi pi-palette"
      @click="drawerVisible = true"
      severity="secondary"
      outlined
      class="w-full"
      aria-label="Open Theme Customizer"
    />

    <Drawer
      v-model:visible="drawerVisible"
      position="right"
      header="Theme Customizer"
      class="!w-full md:!w-80 lg:!w-[34rem]"
    >
      <div class="flex flex-col gap-6">
        <div class="flex items-center">
          <span class="font-medium flex-1">Dark Theme</span>
          <button
            type="button"
            class="inline-flex w-8 h-8 p-0 items-center justify-center border rounded cursor-pointer transition-all hover:bg-emphasis active:scale-95"
            @click="onThemeToggler"
            aria-label="Toggle Dark Theme"
          >
            <i :class="`pi ${iconClass}`" />
          </button>
        </div>

        <div class="flex-col justify-start items-start gap-2 flex">
          <span class="text-sm font-medium">Primary Colors</span>
          <div class="self-stretch justify-start items-start gap-2 inline-flex flex-wrap">
            <button
              v-for="primaryColor of primaryColors"
              :key="primaryColor.name"
              type="button"
              :title="primaryColor.name"
              @click="updateColors('primary', primaryColor)"
              class="outline outline-2 outline-offset-1 outline-transparent cursor-pointer p-0 rounded-[50%] w-5 h-5"
              :style="{
                backgroundColor: `${primaryColor.name === 'noir' ? 'var(--text-color)' : primaryColor.palette['500']}`,
                outlineColor: `${selectedPrimaryColor === primaryColor.name ? 'var(--p-primary-color)' : ''}`,
              }"
            ></button>
          </div>
        </div>

        <div class="flex-col justify-start items-start gap-2 flex">
          <span class="text-sm font-medium">Surface Colors</span>
          <div class="self-stretch justify-start items-start gap-2 inline-flex">
            <button
              v-for="surface of surfaces"
              :key="surface.name"
              type="button"
              :title="surface.name"
              @click="updateColors('surface', surface)"
              class="outline outline-2 outline-offset-1 outline-transparent cursor-pointer p-0 rounded-[50%] w-5 h-5"
              :style="{
                backgroundColor: `${surface.palette['500']}`,
                outlineColor: `${selectedSurfaceColor === surface.name ? 'var(--p-primary-color)' : ''}`,
              }"
            ></button>
          </div>
        </div>

        <div class="flex-col justify-start items-start gap-2 flex w-full">
          <span class="text-sm font-medium">Preset</span>
          <div
            class="inline-flex p-[0.28rem] items-start gap-[0.28rem] rounded-[0.71rem] border border-[#00000003] w-full"
          >
            <SelectButton
              :fluid="true"
              v-model="themeModel"
              @update:modelValue="onPresetChange"
              :options="presets"
              :allowEmpty="false"
            />
          </div>
        </div>

        <div class="flex items-center">
          <span class="font-medium flex-1">Ripple Effect</span>
          <ToggleSwitch :modelValue="rippleActive" @update:modelValue="onRippleChange" />
        </div>
      </div>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { $t, updatePreset, updateSurfacePalette } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import Lara from '@primeuix/themes/lara'
import Nora from '@primeuix/themes/nora'
import Material from '@primeuix/themes/material'
import type { PaletteDesignToken } from '@primeuix/themes/types'
import { usePrimeVue } from 'primevue/config'
import { AppStateKey, type AppState } from '@/plugins/appState'
import { primaryColors, surfaces } from '@/config/colorThemes'

// Access global properties
const $primevue = usePrimeVue()
const $appState = inject<AppState>(AppStateKey)

const themeModel = computed({
  get: () => ($appState ? $appState.theme : ''),
  set: (val) => {
    if ($appState) $appState.theme = val
  },
})

// Theme presets data
const themePresetsData = { Aura, Lara, Nora, Material }
const presets = Object.keys(themePresetsData)

// Reactive state
const iconClass = ref('pi-moon')
const selectedPrimaryColor = ref('noir')
const selectedSurfaceColor = ref<string | null>(null)
const drawerVisible = ref(false)

const rippleActive = computed(() => $primevue.config.ripple)

const storageKey = 'app-settings'

const saveSettings = () => {
  const settings = {
    primaryColor: selectedPrimaryColor.value,
    surfaceColor: selectedSurfaceColor.value,
    theme: $appState?.theme,
    ripple: $primevue.config.ripple,
    dark: document.documentElement.classList.contains('p-dark'),
  }
  localStorage.setItem(storageKey, JSON.stringify(settings))
}

const loadSettings = () => {
  const savedSettings = localStorage.getItem(storageKey)

  if (savedSettings) {
    const settings = JSON.parse(savedSettings)

    // Set reactive state from saved values
    selectedPrimaryColor.value = settings.primaryColor
    selectedSurfaceColor.value = settings.surfaceColor
    if ($appState) {
      $appState.theme = settings.theme
    }
    $primevue.config.ripple = settings.ripple

    // Apply or remove dark mode based on saved setting
    if (settings.dark) {
      document.documentElement.classList.add('p-dark')
      iconClass.value = 'pi-sun'
    } else {
      document.documentElement.classList.remove('p-dark')
      iconClass.value = 'pi-moon'
    }

    // Re-apply the entire theme based on the loaded settings
    // This is crucial for the visual changes to take effect
    onPresetChange(settings.theme)
  }
}

onMounted(() => {
  loadSettings()
})

const onThemeToggler = () => {
  const root = document.getElementsByTagName('html')[0]
  root.classList.toggle('p-dark')
  iconClass.value = iconClass.value === 'pi-moon' ? 'pi-sun' : 'pi-moon'

  saveSettings()
}

const getPresetExt = () => {
  const color = primaryColors.find((c) => c.name === selectedPrimaryColor.value)

  if (!color) {
    return {}
  }

  if (color.name === 'noir') {
    return {
      semantic: {
        primary: {
          50: '{surface.50}',
          100: '{surface.100}',
          200: '{surface.200}',
          300: '{surface.300}',
          400: '{surface.400}',
          500: '{surface.500}',
          600: '{surface.600}',
          700: '{surface.700}',
          800: '{surface.800}',
          900: '{surface.900}',
          950: '{surface.950}',
        },
        colorScheme: {
          light: {
            primary: {
              color: '{primary.950}',
              contrastColor: '#ffffff',
              hoverColor: '{primary.900}',
              activeColor: '{primary.800}',
            },
            highlight: {
              background: '{primary.950}',
              focusBackground: '{primary.700}',
              color: '#ffffff',
              focusColor: '#ffffff',
            },
          },
          dark: {
            primary: {
              color: '{primary.50}',
              contrastColor: '{primary.950}',
              hoverColor: '{primary.100}',
              activeColor: '{primary.200}',
            },
            highlight: {
              background: '{primary.50}',
              focusBackground: '{primary.300}',
              color: '{primary.950}',
              focusColor: '{primary.950}',
            },
          },
        },
      },
    }
  } else {
    if ($appState?.theme === 'Nora') {
      return {
        semantic: {
          primary: color.palette,
          colorScheme: {
            light: {
              primary: {
                color: '{primary.600}',
                contrastColor: '#ffffff',
                hoverColor: '{primary.700}',
                activeColor: '{primary.800}',
              },
              highlight: {
                background: '{primary.600}',
                focusBackground: '{primary.700}',
                color: '#ffffff',
                focusColor: '#ffffff',
              },
            },
            dark: {
              primary: {
                color: '{primary.500}',
                contrastColor: '{surface.900}',
                hoverColor: '{primary.400}',
                activeColor: '{primary.300}',
              },
              highlight: {
                background: '{primary.500}',
                focusBackground: '{primary.400}',
                color: '{surface.900}',
                focusColor: '{surface.900}',
              },
            },
          },
        },
      }
    } else {
      return {
        semantic: {
          primary: color.palette,
          colorScheme: {
            light: {
              primary: {
                color: '{primary.500}',
                contrastColor: '#ffffff',
                hoverColor: '{primary.600}',
                activeColor: '{primary.700}',
              },
              highlight: {
                background: '{primary.50}',
                focusBackground: '{primary.100}',
                color: '{primary.700}',
                focusColor: '{primary.800}',
              },
            },
            dark: {
              primary: {
                color: '{primary.400}',
                contrastColor: '{surface.900}',
                hoverColor: '{primary.300}',
                activeColor: '{primary.200}',
              },
              highlight: {
                background: 'color-mix(in srgb, {primary.400}, transparent 84%)',
                focusBackground: 'color-mix(in srgb, {primary.400}, transparent 76%)',
                color: 'rgba(255,255,255,.87)',
                focusColor: 'rgba(255,255,255,.87)',
              },
            },
          },
        },
      }
    }
  }
}

const applyTheme = (type: string, color: { palette: PaletteDesignToken | undefined }) => {
  if (type === 'primary') {
    updatePreset(getPresetExt())
  } else if (type === 'surface') {
    updateSurfacePalette(color.palette)
  }
}

const updateColors = (
  type: string,
  color: { name: string; palette: PaletteDesignToken | undefined },
) => {
  if (type === 'primary') {
    selectedPrimaryColor.value = color.name
  } else if (type === 'surface') {
    selectedSurfaceColor.value = color.name
  }
  applyTheme(type, color)
  saveSettings()
}

const onRippleChange = (value: boolean) => {
  $primevue.config.ripple = value
  saveSettings()
}

const onPresetChange = (value: keyof typeof themePresetsData) => {
  if ($appState) {
    $appState.theme = value
  }
  const preset = themePresetsData[value]
  const surfacePalette = surfaces.find((s) => s.name === selectedSurfaceColor.value)?.palette

  $t()
    .preset(preset)
    .preset(getPresetExt())
    .surfacePalette(surfacePalette)
    .use({ useDefaultOptions: true })
  saveSettings()
}
</script>

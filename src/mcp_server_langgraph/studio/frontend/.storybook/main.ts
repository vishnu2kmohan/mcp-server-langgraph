import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: [
    "@chromatic-com/storybook",
    "@storybook/addon-a11y",
    "@storybook/addon-docs",
    "@storybook/addon-onboarding",
  ],
  framework: "@storybook/react-vite",
  async viteFinal(config) {
    // Filter out vite-plugin-pwa and its related plugins to avoid conflicts with Storybook
    // PWA plugin causes build failures because Storybook's sb-manager/globals-runtime.js
    // exceeds the maximumFileSizeToCacheInBytes limit (3.15 MB > 2 MiB default)
    if (config.plugins) {
      const pwaPluginNames = [
        "vite-plugin-pwa",
        "vite-plugin-pwa:build",
        "vite-plugin-pwa:dev-sw",
        "vite-plugin-pwa:info",
        "VitePWA",
      ];

      const filterPlugin = (plugin: unknown): boolean => {
        if (!plugin) return false;

        // Handle plugin objects with name property
        if (typeof plugin === "object" && "name" in plugin) {
          const name = (plugin as { name: string }).name;
          return !pwaPluginNames.some((pwaName) => name.includes(pwaName));
        }

        // Handle plugin arrays (some plugins return arrays)
        if (Array.isArray(plugin)) {
          return plugin.every(filterPlugin);
        }

        return true;
      };

      config.plugins = config.plugins.filter(filterPlugin);
    }
    return config;
  },
};
export default config;

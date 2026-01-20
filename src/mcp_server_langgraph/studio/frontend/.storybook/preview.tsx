/**
 * Storybook Preview Configuration
 *
 * Configures global decorators, parameters, and theme switching.
 * Uses @storybook/addon-themes for toolbar-based theme toggling.
 *
 * @see https://storybook.js.org/docs/configure#configure-story-rendering
 * @see https://storybook.js.org/docs/essentials/toolbars-and-globals
 */

import type { Preview } from "@storybook/react-vite";
import {
  withThemeByClassName,
  withThemeByDataAttribute,
} from "@storybook/addon-themes";
import "../src/index.css"; // Import Tailwind CSS with Radix colors

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    // Remove hardcoded backgrounds - themes handle this now
    backgrounds: { disable: true },
    docs: {
      // Ensure docs also respect theme
      theme: undefined,
    },
  },
  decorators: [
    // Padding wrapper for all stories
    (Story) => (
      <div className="p-4">
        <Story />
      </div>
    ),
    // Dark/Light mode toggle via class on html element
    // This matches Tailwind's darkMode: 'class' configuration
    withThemeByClassName({
      themes: {
        light: "light",
        dark: "dark",
      },
      defaultTheme: "light",
    }),
    // Color theme toggle via data attribute on html element
    // This matches our [data-color-theme] CSS selectors
    withThemeByDataAttribute({
      themes: {
        "Violet + Sage": "violet-sage",
        "Teal + Sage": "teal-sage",
        "Violet + Olive": "violet-olive",
        "Teal + Olive": "teal-olive",
      },
      defaultTheme: "Violet + Sage",
      attributeName: "data-color-theme",
    }),
  ],
  // Global toolbar items for theme selection
  globalTypes: {
    // Override default theme toolbar labels
    theme: {
      description: "Appearance mode (light/dark)",
      toolbar: {
        title: "Appearance",
        icon: "circlehollow",
        items: [
          { value: "light", icon: "sun", title: "Light" },
          { value: "dark", icon: "moon", title: "Dark" },
        ],
        dynamicTitle: true,
      },
    },
  },
};

export default preview;

#!/usr/bin/env npx ts-node
/**
 * Toggle Migration Script
 *
 * Migrates raw Button role="switch" patterns to Toggle component.
 * Run: npx ts-node scripts/migrate-toggles.ts
 */

import * as fs from 'fs';
import * as path from 'path';

interface ToggleMigration {
  file: string;
  toggles: {
    id: string;
    label: string;
    description?: string;
    checkedExpr: string;
    onChangeExpr: string;
    disabled?: string;
  }[];
}

// Define migrations for each file
const migrations: ToggleMigration[] = [
  {
    file: 'src/components/Settings/SettingsPanel.tsx',
    toggles: [
      // General tab
      {
        id: 'auto-scroll-toggle',
        label: 'Auto-scroll to new messages',
        checkedExpr: 'preferences.general.autoScroll',
        onChangeExpr: '(checked) => updateGeneralPreferences({ autoScroll: checked })',
      },
      {
        id: 'submit-on-enter-toggle',
        label: 'Press Enter to send messages',
        description: 'submitOnEnter ? "Shift+Enter for new line" : "Use Ctrl+Enter to send"',
        checkedExpr: 'submitOnEnter',
        onChangeExpr: '() => dispatch(setSubmitOnEnter(!submitOnEnter))',
      },
      {
        id: 'notifications-toggle',
        label: 'Enable notifications',
        checkedExpr: 'preferences.general.notificationsEnabled',
        onChangeExpr: '(checked) => updateGeneralPreferences({ notificationsEnabled: checked })',
      },
      {
        id: 'sound-toggle',
        label: 'Sound effects',
        checkedExpr: 'preferences.general.soundEnabled',
        onChangeExpr: '(checked) => updateGeneralPreferences({ soundEnabled: checked })',
      },
      // Accessibility tab
      {
        id: 'reduced-motion-toggle',
        label: 'Reduce motion',
        description: 'Minimize animations and transitions',
        checkedExpr: 'preferences.accessibility.reducedMotion',
        onChangeExpr: '(checked) => updateAccessibilityPreferences({ reducedMotion: checked })',
      },
      {
        id: 'high-contrast-toggle',
        label: 'High contrast mode',
        description: 'Increase color contrast for better visibility',
        checkedExpr: 'preferences.accessibility.highContrast',
        onChangeExpr: '(checked) => updateAccessibilityPreferences({ highContrast: checked })',
      },
      {
        id: 'screen-reader-toggle',
        label: 'Screen reader optimized',
        description: 'Optimize UI for screen reader usage',
        checkedExpr: 'preferences.accessibility.screenReaderMode',
        onChangeExpr: '(checked) => updateAccessibilityPreferences({ screenReaderMode: checked })',
      },
      // Privacy tab
      {
        id: 'analytics-toggle',
        label: 'Usage analytics',
        description: 'Help improve the product by sharing anonymous usage data',
        checkedExpr: 'preferences.privacy.analyticsEnabled',
        onChangeExpr: '(checked) => updatePrivacyPreferences({ analyticsEnabled: checked })',
      },
      {
        id: 'error-reporting-toggle',
        label: 'Error reporting',
        description: 'Automatically send error reports to help fix issues',
        checkedExpr: 'preferences.privacy.errorReporting',
        onChangeExpr: '(checked) => updatePrivacyPreferences({ errorReporting: checked })',
      },
      {
        id: 'personalization-toggle',
        label: 'Personalization',
        description: 'Allow personalized suggestions based on your usage',
        checkedExpr: 'preferences.privacy.personalization',
        onChangeExpr: '(checked) => updatePrivacyPreferences({ personalization: checked })',
      },
      // HITL tab
      {
        id: 'hitl-enabled-toggle',
        label: 'Enable Human-in-the-Loop',
        description: 'Require approval for agent actions',
        checkedExpr: 'preferences.hitl.enabled',
        onChangeExpr: '(checked) => updateHITLPreferences({ enabled: checked })',
      },
      {
        id: 'hitl-push-toggle',
        label: 'Push notifications',
        description: 'Get notified when an agent needs your approval',
        checkedExpr: 'preferences.hitl.pushNotificationsEnabled',
        onChangeExpr: '(checked) => updateHITLPreferences({ pushNotificationsEnabled: checked })',
      },
      {
        id: 'hitl-email-toggle',
        label: 'Email notifications',
        description: 'Receive email when approval is needed',
        checkedExpr: 'preferences.hitl.emailNotificationsEnabled',
        onChangeExpr: '(checked) => updateHITLPreferences({ emailNotificationsEnabled: checked })',
      },
    ],
  },
];

function generateToggleCode(toggle: ToggleMigration['toggles'][0]): string {
  const props = [
    `id="${toggle.id}"`,
    `checked={${toggle.checkedExpr}}`,
    `onChange={${toggle.onChangeExpr}}`,
    `label="${toggle.label}"`,
  ];

  if (toggle.description) {
    // Check if description is a JS expression or a string
    if (toggle.description.includes('?') || toggle.description.includes('{')) {
      props.push(`description={${toggle.description}}`);
    } else {
      props.push(`description="${toggle.description}"`);
    }
  }

  if (toggle.disabled) {
    props.push(`disabled={${toggle.disabled}}`);
  }

  return `<Toggle\n                  ${props.join('\n                  ')}\n                />`;
}

// Main execution
console.log('Toggle Migration Script');
console.log('======================\n');

for (const migration of migrations) {
  console.log(`File: ${migration.file}`);
  console.log(`Toggles to migrate: ${migration.toggles.length}`);
  console.log('\nGenerated Toggle components:\n');

  for (const toggle of migration.toggles) {
    console.log(`// ${toggle.id}`);
    console.log(generateToggleCode(toggle));
    console.log();
  }
}

console.log('\nNote: This script generates the replacement code.');
console.log('Manual replacement is needed due to varied surrounding context.');

/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  // Vite built-in environment variables
  readonly MODE: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly SSR: boolean;
  readonly BASE_URL: string;

  // Custom environment variables
  readonly VITE_API_BASE_URL: string;
  readonly VITE_WS_BASE_URL: string;
  readonly VITE_KEYCLOAK_URL: string;
  readonly VITE_KEYCLOAK_REALM: string;
  readonly VITE_KEYCLOAK_CLIENT_ID: string;
  readonly VITE_VAPID_PUBLIC_KEY: string;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// PWA virtual module types
declare module "virtual:pwa-register" {
  import type { RegisterSWOptions } from "vite-plugin-pwa/types";

  export function registerSW(
    options?: RegisterSWOptions,
  ): (reloadPage?: boolean) => Promise<void>;
}

declare module "virtual:pwa-register/react" {
  import type { RegisterSWOptions } from "vite-plugin-pwa/types";
  import type { Dispatch, SetStateAction } from "react";

  export function useRegisterSW(options?: RegisterSWOptions): {
    needRefresh: [boolean, Dispatch<SetStateAction<boolean>>];
    offlineReady: [boolean, Dispatch<SetStateAction<boolean>>];
    updateServiceWorker: (reloadPage?: boolean) => Promise<void>;
  };
}

// Background Sync API type augmentation
// These types are not included in TypeScript's standard DOM lib
interface SyncManager {
  register(tag: string): Promise<void>;
  getTags(): Promise<string[]>;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface SyncEvent extends ExtendableEvent {
  readonly tag: string;
}

declare global {
  interface ServiceWorkerRegistration {
    readonly sync?: SyncManager;
  }
}

// Make this file a module to enable `declare global` augmentation
export {};

import type { OkofficeAPI } from '../../preload/api-types';

const api = (window as unknown as { okoffice: OkofficeAPI }).okoffice;

if (!api) {
  throw new Error(
    'okoffice API not found on window. Ensure the preload script loaded correctly.',
  );
}

export default api;

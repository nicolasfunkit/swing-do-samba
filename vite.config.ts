import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  // Chemins relatifs : le dossier dist/ fonctionne à la racine d'un site
  // comme dans un sous-dossier (GitHub Pages, par exemple).
  base: './',
  plugins: [svelte()],
});

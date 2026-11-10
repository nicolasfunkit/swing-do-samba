import { mount } from 'svelte';
import App from './App.svelte';

mount(App, { target: document.getElementById('app')! });

// Hors ligne et installation : uniquement sur le build de production.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}

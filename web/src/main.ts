import { createApp } from "vue";
import App from "./App.vue";
import { createHaxjobsRouter } from "./router";
import { initializeAppStatePersistence } from "./state/app-state";
import "./style.css";

initializeAppStatePersistence();

createApp(App).use(createHaxjobsRouter()).mount("#app");

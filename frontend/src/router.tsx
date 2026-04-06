import {
  createRouter,
  createRoute,
  createRootRoute,
  redirect,
  Outlet,
} from "@tanstack/react-router";
import Layout from "@/components/layout";
import LoginPage from "@/pages/login";
import ObrasPage from "@/pages/obras";
import DiarioPage from "@/pages/diario";
import DashboardPage from "@/pages/dashboard";
import UsuariosPage from "@/pages/usuarios";

// Root route — renders either login or layout
const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

// Login
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
});

// Authenticated layout wrapper
const authLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "auth",
  component: () => (
    <Layout>
      <Outlet />
    </Layout>
  ),
  beforeLoad: () => {
    if (!localStorage.getItem("token")) {
      throw redirect({ to: "/login" });
    }
  },
});

// Obras list
const obrasRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/obras",
  component: ObrasPage,
});

// Diario
const diarioRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/obras/$obraId/diario/$data",
  component: DiarioPage,
});

// Dashboard
const dashboardRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/dashboard",
  component: DashboardPage,
});

// Usuarios
const usuariosRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/usuarios",
  component: UsuariosPage,
});

// Index redirect
const indexRoute = createRoute({
  getParentRoute: () => authLayoutRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/obras" });
  },
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  authLayoutRoute.addChildren([indexRoute, obrasRoute, diarioRoute, dashboardRoute, usuariosRoute]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

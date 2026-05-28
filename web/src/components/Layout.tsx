import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <header
        style={{
          padding: "1rem 2rem",
          borderBottom: "1px solid #2d3748",
          display: "flex",
          alignItems: "center",
          gap: "2rem",
        }}
      >
        <span style={{ fontWeight: 700, fontSize: "1.1rem", color: "#e2e8f0" }}>
          Mini Exchange
        </span>
        <nav aria-label="Main navigation">
          <ul
            style={{
              display: "flex",
              gap: "1.5rem",
              listStyle: "none",
              margin: 0,
              padding: 0,
            }}
          >
            <li>
              <NavLink
                to="/submit-order"
                style={({ isActive }) => ({
                  color: isActive ? "#90cdf4" : "#63b3ed",
                  fontWeight: isActive ? 600 : 400,
                  borderBottom: isActive ? "2px solid #90cdf4" : "none",
                  paddingBottom: "2px",
                })}
              >
                Submit Order
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/status"
                style={({ isActive }) => ({
                  color: isActive ? "#90cdf4" : "#63b3ed",
                  fontWeight: isActive ? 600 : 400,
                  borderBottom: isActive ? "2px solid #90cdf4" : "none",
                  paddingBottom: "2px",
                })}
              >
                Order Status
              </NavLink>
            </li>
          </ul>
        </nav>
      </header>
      <main
        role="main"
        style={{ flex: 1, padding: "2rem" }}
      >
        <Outlet />
      </main>
    </div>
  );
}

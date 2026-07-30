import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { Menu, Layout } from "antd";
import Dashboard from "./pages/Dashboard";
import Chatbot from "./pages/Chatbot";
import AuditPanel from "./pages/AuditPanel";

const { Header, Content } = Layout;

function Gezinme() {
  const { pathname } = useLocation();
  return (
    <Menu
      mode="horizontal"
      theme="dark"
      selectedKeys={[pathname]}
      items={[
        { key: "/", label: <Link to="/">Dashboard</Link> },
        { key: "/chatbot", label: <Link to="/chatbot">Chatbot</Link> },
        { key: "/audit", label: <Link to="/audit">Juri Audit Paneli</Link> },
      ]}
    />
  );
}

function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: "100vh" }}>
        <Header style={{ display: "flex", alignItems: "center" }}>
          <Gezinme />
        </Header>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chatbot" element={<Chatbot />} />
            <Route path="/audit" element={<AuditPanel />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  );
}

export default App;

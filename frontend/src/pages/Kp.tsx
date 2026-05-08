import { Navigate } from "react-router";
import { useCurrentUser } from "../context/useCurrentUser";
import KpCompanyEvents from "./KpCompanyEvents";
import KpCompanyView from "./KpCompanyView";
import KpDashboard from "./KpDashboard";
import KpManage from "./KpManage";
import { useParams } from "react-router";

const Kp = () => {
  const { user } = useCurrentUser();
  const { id } = useParams<{ id?: string }>();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.is_staff || user.is_admin) {
    return id ? <KpManage /> : <KpDashboard />;
  }

  if (user.company_id) {
    return id ? <KpCompanyView /> : <KpCompanyEvents />;
  }

  return <Navigate to="/not-allowed" replace />;
};
export default Kp;

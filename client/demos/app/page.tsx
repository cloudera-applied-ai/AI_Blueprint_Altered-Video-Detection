import { redirect } from "next/navigation";
import { defaultLandingPath } from "./lib/appRole";

export default function Home() {
  redirect(defaultLandingPath());
}

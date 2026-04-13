import { Suspense } from "react";
import CustomVoicesLibrary from "@/components/CustomVoicesLibrary";

function CustomVoicesFallback() {
  return <div className="p-6">Loading custom voices...</div>;
}

export default function CustomVoicesPage() {
  return (
    <Suspense fallback={<CustomVoicesFallback />}>
      <CustomVoicesLibrary />
    </Suspense>
  );
}
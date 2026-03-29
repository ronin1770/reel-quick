import CreateTextOverlayPage from "@/components/CreateTextOverlayPage";

type CreateTextOverlayRouteProps = {
  params: Promise<{
    videoId: string;
  }>;
};

export default async function CreateTextOverlayRoute({
  params,
}: CreateTextOverlayRouteProps) {
  const { videoId } = await params;
  return <CreateTextOverlayPage videoId={videoId} />;
}

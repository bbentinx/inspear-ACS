import { DeviceDetailView } from "@/components/device-detail-view";

export default async function DeviceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DeviceDetailView id={id} />;
}
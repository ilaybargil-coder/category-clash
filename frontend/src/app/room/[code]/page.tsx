import GameRoom from "@/components/GameRoom";

export default async function RoomPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  return <GameRoom code={code.toUpperCase()} />;
}

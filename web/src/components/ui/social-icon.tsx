import {
  SiFacebook,
  SiInstagram,
  SiTiktok,
  SiWhatsapp,
  SiYoutube,
} from "react-icons/si";
import type { IconType } from "react-icons";
import { cn } from "@/lib/utils";

const icons: Record<string, { bg: string; Icon: IconType; color: string }> = {
  instagram: {
    bg: "bg-gradient-to-br from-[#f58529] via-[#dd2a7b] to-[#8134af]",
    Icon: SiInstagram,
    color: "text-white",
  },
  tiktok: {
    bg: "bg-black ring-1 ring-white/15",
    Icon: SiTiktok,
    color: "text-white",
  },
  youtube: {
    bg: "bg-[#FF0000]",
    Icon: SiYoutube,
    color: "text-white",
  },
  facebook: {
    bg: "bg-[#1877F2]",
    Icon: SiFacebook,
    color: "text-white",
  },
  whatsapp: {
    bg: "bg-[#25D366]",
    Icon: SiWhatsapp,
    color: "text-white",
  },
};

export function SocialIcon({ id, className }: { id: string; className?: string }) {
  const brand = icons[id];
  if (!brand) {
    return (
      <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl bg-muted text-xs font-bold", className)}>
        ?
      </span>
    );
  }
  const { Icon, bg, color } = brand;
  return (
    <span
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-sm",
        bg,
        className,
      )}
      aria-hidden
    >
      <Icon className={cn("h-5 w-5", color)} />
    </span>
  );
}
"use strict";
function restaurantURL(path) {
  const root =
    document.querySelector('meta[name="restaurant-root"]')?.content || "";
  if (
    typeof path !== "string" ||
    !path.startsWith("/") ||
    path.startsWith("//") ||
    (root && (path === root || path.startsWith(root + "/")))
  )
    return path;
  return root + path;
}

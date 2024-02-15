import m from "mithril";
import ArticleList from "./ArticleList";

m.route(document.body, "/list", {
    "/list": ArticleList
})

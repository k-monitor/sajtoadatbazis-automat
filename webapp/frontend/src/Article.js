import m from "mithril";

var Article = {
    list: [],
    pages: 0,
    page: 1,
    loadList: function() {
        return m.request({
            method: "GET",
            url: "http://kmonitordemo.duckdns.org/api/articles?page="+Article.page,
        })
        .then(function(result) {
            console.log(result)
	for (let article of result.articles) {
		if (article.people == null)
			article.people = "";
		if (article.institutions == null)
			article.institutions = "";
		if (article.corrupt_people == null)
			article.corrupt_people = "";
		if (article.corrupt_institutions == null)
			article.corrupt_institutions = "";
		if (article.tags == null)
			article.tags = "";
		
		if (article.selected == null)
			article.selected = new Map();
		if (article.selectedPeople == null)
			article.selectedPeople = new Map();
		if (article.selectedInstitutions == null)
			article.selectedInstitutions = new Map();

		for(let p of article.corrupt_people.split(", "))
			article.selectedPeople.set(p, true);
		for(let p of article.corrupt_institutions.split(", "))
			article.selectedInstitutions.set(p, true);
		for(let p of article.tags.split(", "))
			article.selected.set(p, true);
	}
            console.log(result)
            Article.list = result.articles
            Article.pages = result.pages
        })
    },
}

export default Article

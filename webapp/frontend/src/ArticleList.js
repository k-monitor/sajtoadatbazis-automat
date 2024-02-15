import m from "mithril";
import Article from "./Article";
import { ListItem, Dialog, SelectList, Classes, Input, Button, Icons, Card, ButtonGroup } from 'construct-ui';

function itemPredicate(query, item) {
    return item.toLowerCase().includes(query.toLowerCase());
}

function selectItem(item, items) {
    if (items.has(item))
        items.delete(item);
    else
        items.set(item, true)
} 

function onselectIntitutions(item) {
    if (selectedInstitutions.has(item))
        selectedInstitutions.delete(item);
    else
        selectedInstitutions.set(item, true)
} 

function onselect(item) {
    if (selected.has(item))
        selected.delete(item);
    else
        selected.set(item, true)
} 

var ArticleList = {
    oninit: Article.loadList,
    isOpen: false,
    view: function() {
        return m("[style=padding:30px]", [Article.list.map(function(article) {
            return m(Card, [
                m("h4", article.title),
                m("div", article.lead),
                m("date", article.date),
                m(ButtonGroup, {}, [
                    m(Button, {iconLeft: Icons.X, intent: 'none', label: 'Mégse', onclick: e => m.request({
                        method: "POST",
                        url: "http://kmonitordemo.duckdns.org/api/not_corruption",
                        body: {
                            id: article.id,
                        },
                    }).then(function(result) {
                        console.log(result);
                        Article.loadList();
                    }),
                }),
                    m(Button, {iconLeft: Icons.CHECK, intent: 'primary', label: 'Tovább', onclick: e => article.isOpen=true}),
                ]),
                m(Dialog, {
                    content: m("[style=padding:10px]", [
                        m("p", "URL"),
                        m(Input, { autofocus: true, fluid: true, defaultValue: article.url}),
                        m("p[style=padding-top:10px]", "Cím"),
                        m(Input, { autofocus: true, fluid: true, defaultValue: article.title}),
                        m("p[style=padding-top:10px]", "Lead"),
                        m(Input, { autofocus: true, fluid: true, defaultValue: article.description}),
                        m("p[style=padding-top:10px]", "Szöveg"),
                        m("div", [
                            m('textarea.text-class', {
                                style: "width:100%;height:200px",
                                spellcheck: false,
                                defaultValue: article.text,
                            }),
                        ]),
                        m(SelectList, {
                            closeOnSelect: false,
                            items: article.people.split(", "),
                            itemRender: item => m(ListItem, {
                                label: item,
                                selected: article.selectedPeople.has(item)
                            }),
                            trigger: m(Button, {
                                align: 'left',
                                compact: true,
                                iconright: Icons.CHEVRON_DOWN,
                                sublabel: 'személyek:',
                                label: Array.from(article.selectedPeople.keys()).sort().toString(),
                                style: "width:100%",
                            }),
                            itemPredicate: itemPredicate,
                            onSelect: item => selectItem(item, article.selectedPeople),
                        }),
			m(SelectList, {
                            closeOnSelect: false,
                            items: article.institutions.split(", "),
                            itemRender: item => m(ListItem, {
                                label: item,
                                selected: article.selectedInstitutions.has(item)
                            }),
                            trigger: m(Button, {
                                align: 'left',
                                compact: true,
                                iconright: Icons.CHEVRON_DOWN,
                                sublabel: 'intézmények:',
                                label: Array.from(article.selectedInstitutions.keys()).sort().toString(),
                                style: "width:100%",
                            }),
                            itemPredicate: itemPredicate,
                            onSelect: item => selectItem(item, article.selectedInstitutions),
                         }),
                         m(SelectList, {
                            closeOnSelect: false,
                            items: article.tags.split(", "),
                            itemRender: item => m(ListItem, {
                                label: item,
                                selected: article.selected.has(item)
                            }),
                            trigger: m(Button, {
                                align: 'left',
                                compact: true,
                                iconright: Icons.CHEVRON_DOWN,
                                sublabel: 'címkék:',
                                label: Array.from(article.selected.keys()).sort().toString(),
                                style: "width:100%",
                            }),
                            itemPredicate: itemPredicate,
                            onSelect: item => selectItem(item, article.selected),
                        }),
                   ]),
                    isOpen: article.isOpen,
                    title: 'Cikk szerkesztése',
                    footer: m(`.${Classes.ALIGN_RIGHT}`, [
                      m(Button, {
                        label: 'Mégse',
                        onclick: e => article.isOpen=false,
                      }),
                      m(Button, {
                        label: 'Küldés',
                        intent: 'primary',
                        onclick: e => {
                            return m.request({
                                method: "POST",
                                url: "http://kmonitordemo.duckdns.org/api/annote",
                                body: {
                                    id: article.id,
                                    url: article.url,
                                    title: article.title,
                                    description: article.description,
                                    text: article.text,
                                    relations: article.relations,
                                    people: Array.from(selectedPeople.keys()),
                                    corrupt_people: Array.from(selectedPeople.keys()),
                                    institutions: Array.from(selectedPeople.keys()),
                                    corrupt_institutions: Array.from(selectedPeople.keys()),
                                    tags: Array.from(selected.keys()),
                                },
                            })
                            .then(function(result) {
                                console.log(result);
                                article.isOpen = false;
                            });
                        },
                      })
                    ])
                  })
            ])
        }),
        m(ButtonGroup, {}, Array.apply(null, Array(Article.pages)).map((_,n) => n+1).filter(n => n == 1 || n == Article.pages || Math.abs(n-Article.page) < 3).map(i => {
            return m(Button, {intent: i == Article.page ? 'primary' : 'none', label: i, onclick: e => (Article.page=i) && Article.loadList()});
        })),
    ])
    }
}

export default ArticleList

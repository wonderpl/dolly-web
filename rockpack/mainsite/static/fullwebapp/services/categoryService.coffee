###
  Used to Manage the category menu.
  If locale did not change, a cached version of the data will be retrived
###

angular.module('WebApp').factory('categoryService', [ '$http', 'locale', 'apiUrl', '$q', ($http, locale, apiUrl, $q) ->

  compareDecending = (a, b) ->
    a = a.priority
    b = b.priority

    if (a != b)
      if (a < b || typeof a == 'undefined')
        return 1
      if (a > b || typeof b == 'undefined')
        return -1
    return 1


  Categories = {
    items: []
    locale: null
    fetchCategories: () ->
      if locale != Categories.locale
        Categories.locale = locale
        $http({
          method: 'GET',
          params: locale
          url: apiUrl.categories,
        })
        .then(((data) ->
          data.data.categories.items.sort(compareDecending)
          _.each(data.data.categories.items, (category) ->
            tempcategory = []
            _.each(category.sub_categories, (subcategory) ->
              if subcategory.priority > 0
                tempcategory.push(subcategory)
            )
            category.sub_categories = tempcategory
            category.sub_categories.sort(compareDecending)

          )
          Categories.items = data.data.categories.items
          return data.data.categories.items
        ),
        (data) ->
          console.log data
        )
      else
        deferred = $q.defer()
        deferred.resolve(Categories.items)
        return deferred.promise
  }

  return Categories

])
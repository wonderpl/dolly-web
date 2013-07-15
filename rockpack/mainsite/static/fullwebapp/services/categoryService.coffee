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
      Categories.locale = locale
      $http({
        method: 'GET',
        params: locale
        url: apiUrl.categories,
      })
      .then(((data) ->
        console.log 'fetched'
        tempCategories = []
        for key, value of data.data.categories.items
          if data.data.categories.items[key].priority > 0
            tempCategories.push(data.data.categories.items[key])

        tempCategories.sort(compareDecending)
        _.each(tempCategories, (category) ->
          tempcategory = []
          _.each(category.sub_categories, (subcategory) ->
            if subcategory.priority > 0
              tempcategory.push(subcategory)
          )
          category.sub_categories = tempcategory
          category.sub_categories.sort(compareDecending)
        )
        return tempCategories
      ),
      (data) ->
        console.log data
      )
  }

  return Categories

])
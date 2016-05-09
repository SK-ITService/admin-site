$(function(){
    var SecurityEventList = function(container_elem, template_container_id) {
        this.elem = $(container_elem)
        this.searchConditions = {}
        this.searchUrl = window.bibos_security_event_search_url || './search/'
        this.statusSelectors = []
        BibOS.addTemplate('securityevent-entry', template_container_id);
    }
    $.extend(SecurityEventList.prototype, {
        init: function() {
            var securityeventsearch = this
            $('#securityeventsearch-status-selectors input:checkbox').change(function() {
                securityeventsearch.search();
            })
            $('#securityeventsearch-length-limitation input:radio').change(function() {
                securityeventsearch.search();
            })
            securityeventsearch.search();
        },

        appendEntries: function(dataList) {
            var container = this.elem
            $.each(dataList, function() {
                var info_button = '';
                if(this.has_info) {
                    info_button = '<button ' +
                        'class="btn securityeventinfobutton" ' +
                        'title="Event-info" ' +
                        'data-pk="' + this.pk + '"'+
                    '><i class="icon-info-sign"></i></button>'
                }
                var item = $(BibOS.expandTemplate(
                    'securityevent-entry',
                    $.extend(this, {
                        'securityeventinfobutton': info_button
                    })
                ));
                item.find('input:checkbox').click(function() {
                    $(this).parents('tr').toggleClass('marked');
                });
                item.appendTo(container)
            });
            BibOS.setupJobInfoButtons(container);
        },

        replaceEntries: function(dataList) {
            this.elem.find('tr.muted').remove()
            this.appendEntries(dataList)
        },

        selectFilter: function(field, elem, val) {
            var e = $(elem)
            if(e.hasClass('selected')) {
                e.removeClass('selected');
                val = ''
            } else {
                e.parent().find('li').removeClass('selected');
                e.addClass('selected');
            }
            $('#securityeventsearch-filterform input[name=' + field + ']').val(val)
            this.search()
        },

        selectBatch: function(elem, val) {
            this.selectFilter('batch', elem, val)
        },

        selectPC: function(elem, val) {
            this.selectFilter('pc', elem, val)
        },

        selectGroup: function(elem, val) {
            this.selectFilter('group', elem, val)
        },

        orderby: function(order) {
            $('.orderby').each(function() {
              if ($(this).hasClass('order-' + order)) {
                $(this).addClass('active').find('i').toggleClass('icon-chevron-down icon-chevron-up').addClass('icon-white');
              } else {
                $(this).removeClass('active').find('i').attr('class', 'icon-chevron-down');
              };
            });
            
            var input = $('#securityeventsearch-filterform input[name=orderby]');
            input.val(BibOS.getOrderBy(input.val(), order))
            this.search()
        },

        search: function() {
            var js = this;
            js.searchConditions = $('#securityeventsearch-filterform').serialize()
            $.ajax({
                type: "POST",
                url: js.searchUrl,
                data: js.searchConditions,
                success: function(data) {
                    js.replaceEntries(data)
                },
                dataType: "json"
            });
        },

        reset: function() {
            $('#securityeventsearch-filterform')[0].reset()
            $('#securityeventsearch-filterform li.selected').removeClass('selected')
            $('#securityeventsearch-filterform input[name=batch]').val('')
            $('#securityeventsearch-filterform input[name=pc]').val('')
            $('#securityeventsearch-filterform input[name=group]').val('')
            this.search()
        }
    });
    BibOS.SecurityEventList = new SecurityEventList('#securityevent-list', '#securityeventitem-template');
    $(function() { BibOS.SecurityEventList.init() })
})

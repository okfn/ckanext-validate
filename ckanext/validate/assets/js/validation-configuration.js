/**
 * Interactive builder for Frictionless validation configurations.
 *
 * This module manages the client-side behavior of the validation rules form:
 *
 * - Reads the Frictionless schema stored in the hidden `schema` field.
 * - Displays the existing rules in the rules table.
 * - Adds, edits, enables, disables, and removes rules without reloading the page.
 * - Validates and converts rule values entered by the user.
 * - Builds the corresponding Frictionless field types and constraints.
 * - Stores custom rule metadata, such as error messages and enabled status.
 * - Serializes the updated schema back into the hidden field before submission.
 * - Handles navigation between existing validation configurations.
 *
 * This module does not persist data directly and does not replace server-side
 * validation. The final descriptor is submitted to the CKAN action, where it is
 * validated and normalized by Frictionless before being stored.
 */


this.ckan.module('validation-configuration-builder', function ($) {
  'use strict';

  var RULES = {
    required: {valueType: 'boolean'},
    unique: {valueType: 'boolean'},
    minLength: {valueType: 'integer'},
    maxLength: {valueType: 'integer'},
    minimum: {valueType: 'number'},
    maximum: {valueType: 'number'},
    pattern: {valueType: 'string'},
    enum: {valueType: 'list'}
  };

  return {
    initialize: function () {
      this.schemaInput = this.el.find('[data-role="schema"]');
      this.form = this.el.find('[data-role="configuration-form"]');
      this.selector = this.el.find('[data-role="configuration-selector"]');
      this.ruleIdInput = this.el.find('[data-role="rule-id"]');
      this.fieldInput = this.el.find('[data-role="field-name"]');
      this.fieldTypeInput = this.el.find('[data-role="field-type"]');
      this.ruleTypeInput = this.el.find('[data-role="rule-type"]');
      this.valueInput = this.el.find('[data-role="rule-value"]');
      this.messageInput = this.el.find('[data-role="rule-message"]');
      this.defaultValuePlaceholder = this.valueInput.attr('placeholder') || '';
      this.addButton = this.el.find('[data-role="add-rule"]');
      this.addButtonLabel = this.el.find('[data-role="add-rule-label"]');
      this.cancelButton = this.el.find('[data-role="cancel-edit"]');
      this.errorBox = this.el.find('[data-role="rule-error"]');
      this.ruleList = this.el.find('[data-role="rule-list"]');
      this.fieldList = this.el.find('[data-role="field-list"]');

      this.schema = this._readSchema();
      this.rules = this._readRules();
      this._bootstrapRulesFromSchema();
      this._bindEvents();
      this._updateValueInput();
      this._applyRulesToSchema();
      this._render();
    },

    _bindEvents: function () {
      var module = this;

      this.selector.on('change', function () {
        var target = $(this).val();
        if (target) {
          window.location.assign(target);
        }
      });

      this.addButton.on('click', function () {
        module._saveRule();
      });

      this.cancelButton.on('click', function () {
        module._resetEditor();
      });

      this.ruleTypeInput.on('change', function () {
        module._updateValueInput();
      });

      this.fieldInput.on('change blur', function () {
        module._selectExistingFieldType();
      });

      this.form.on('submit', function () {
        module._applyRulesToSchema();
      });

      this.ruleList.on('click', '[data-action]', function () {
        var button = $(this);
        var id = button.attr('data-rule-id');
        var action = button.attr('data-action');

        if (action === 'edit') {
          module._editRule(id);
        } else if (action === 'toggle') {
          module._toggleRule(id);
        } else if (action === 'delete') {
          module._deleteRule(id);
        }
      });
    },

    _readSchema: function () {
      var raw = this.schemaInput.val();
      var schema;

      try {
        schema = raw ? JSON.parse(raw) : {};
      } catch (error) {
        schema = {};
      }

      if (!schema || typeof schema !== 'object' || Array.isArray(schema)) {
        schema = {};
      }

      if (!Array.isArray(schema.fields)) {
        schema.fields = [];
      }

      return schema;
    },

    _readRules: function () {
      if (!Array.isArray(this.schema._validate_rules)) {
        return [];
      }

      return this.schema._validate_rules.map(function (rule) {
        return {
          id: rule.id || this._newId(),
          field: String(rule.field || '').trim(),
          fieldType: rule.fieldType || 'string',
          constraint: rule.constraint || 'required',
          value: rule.value,
          message: rule.message || '',
          enabled: rule.enabled !== false
        };
      }, this).filter(function (rule) {
        return rule.field && RULES[rule.constraint];
      });
    },

    _bootstrapRulesFromSchema: function () {
      var module = this;

      this.schema.fields.forEach(function (field) {
        var constraints = field.constraints || {};

        Object.keys(constraints).forEach(function (constraint) {
          if (!RULES[constraint]) {
            return;
          }

          var existing = module.rules.some(function (rule) {
            return rule.field === field.name && rule.constraint === constraint;
          });

          if (!existing) {
            module.rules.push({
              id: module._newId(),
              field: field.name,
              fieldType: field.type || 'string',
              constraint: constraint,
              value: constraints[constraint],
              message: '',
              enabled: true
            });
          }
        });

        module.rules.forEach(function (rule) {
          if (rule.field === field.name) {
            rule.fieldType = field.type || rule.fieldType || 'string';
          }
        });
      });
    },

    _saveRule: function () {
      this._hideError();

      var id = this.ruleIdInput.val();
      var field = $.trim(this.fieldInput.val());
      var fieldType = this.fieldTypeInput.val();
      var constraint = this.ruleTypeInput.val();
      var message = $.trim(this.messageInput.val());
      var value;

      if (!field || !fieldType || !RULES[constraint]) {
        this._showError(this._text('required-message'));
        return;
      }

      try {
        value = this._parseValue(constraint, this.valueInput.val(), fieldType);
      } catch (error) {
        this._showError(this._text('invalid-value-message'));
        return;
      }

      var duplicate = this.rules.some(function (rule) {
        return rule.id !== id &&
          rule.field === field &&
          rule.constraint === constraint;
      });

      if (duplicate) {
        this._showError(this._text('duplicate-message'));
        return;
      }

      this.rules.forEach(function (rule) {
        if (rule.field === field) {
          rule.fieldType = fieldType;
        }
      });

      if (id) {
        var existing = this._findRule(id);
        if (!existing) {
          return;
        }

        existing.field = field;
        existing.fieldType = fieldType;
        existing.constraint = constraint;
        existing.value = value;
        existing.message = message;
      } else {
        this.rules.push({
          id: this._newId(),
          field: field,
          fieldType: fieldType,
          constraint: constraint,
          value: value,
          message: message,
          enabled: true
        });
      }

      this._applyRulesToSchema();
      this._render();
      this._resetEditor();
    },

    _parseValue: function (constraint, rawValue, fieldType) {
      var definition = RULES[constraint];
      var value = $.trim(rawValue || '');

      if (definition.valueType === 'boolean') {
        return true;
      }

      if (definition.valueType === 'integer') {
        if (!/^\d+$/.test(value)) {
          throw new Error('invalid integer');
        }

        return parseInt(value, 10);
      }

      if (definition.valueType === 'number') {
        if (!value || !isFinite(Number(value))) {
          throw new Error('invalid number');
        }

        return Number(value);
      }

      if (definition.valueType === 'list') {
        var items = value.split(',').map(function (item) {
          return $.trim(item);
        }).filter(function (item) {
          return item.length > 0;
        });

        if (!items.length) {
          throw new Error('empty list');
        }

        return items.map(function (item) {
          if (fieldType === 'integer') {
            if (!/^-?\d+$/.test(item)) {
              throw new Error('invalid integer list value');
            }
            return parseInt(item, 10);
          }

          if (fieldType === 'number') {
            if (!isFinite(Number(item))) {
              throw new Error('invalid number list value');
            }
            return Number(item);
          }

          if (fieldType === 'boolean') {
            if (item.toLowerCase() === 'true') {
              return true;
            }
            if (item.toLowerCase() === 'false') {
              return false;
            }
            throw new Error('invalid boolean list value');
          }

          return item;
        });
      }

      if (!value) {
        throw new Error('empty value');
      }

      return value;
    },

    _applyRulesToSchema: function () {
      var module = this;
      var managedConstraints = Object.keys(RULES);

      this.schema.fields.forEach(function (field) {
        if (!field.constraints) {
          return;
        }

        managedConstraints.forEach(function (constraint) {
          delete field.constraints[constraint];
        });

        if (!Object.keys(field.constraints).length) {
          delete field.constraints;
        }
      });

      this.rules.forEach(function (rule) {
        var field = module._ensureField(rule.field, rule.fieldType);
        field.type = rule.fieldType;

        if (!rule.enabled) {
          return;
        }

        if (!field.constraints) {
          field.constraints = {};
        }

        field.constraints[rule.constraint] = rule.value;
      });

      this.schema._validate_rules = this.rules;
      this.schemaInput.val(JSON.stringify(this.schema, null, 2));
    },

    _ensureField: function (name, type) {
      var field = this.schema.fields.find(function (item) {
        return item.name === name;
      });

      if (!field) {
        field = {
          name: name,
          type: type || 'string'
        };
        this.schema.fields.push(field);
      }

      return field;
    },

    _render: function () {
      var module = this;
      this.ruleList.empty();

      if (!this.rules.length) {
        $('<tr>')
          .append(
            $('<td>')
              .attr('colspan', 5)
              .addClass('validation-rules-table__empty')
              .text(this._text('empty-message'))
          )
          .appendTo(this.ruleList);
      } else {
        this.rules.forEach(function (rule) {
          module._renderRule(rule);
        });
      }

      this._renderFieldList();
    },

    _renderRule: function (rule) {
      var row = $('<tr>')
        .toggleClass('is-disabled', !rule.enabled);

      $('<td>')
        .append(
          $('<span>')
            .addClass('validation-rules-table__field-name')
            .text(rule.field)
        )
        .appendTo(row);

      $('<td>')
        .append(
          $('<span>')
            .addClass('validation-rules-table__rule-name')
            .text(this._optionText(this.ruleTypeInput, rule.constraint))
        )
        .append(
          $('<small>')
            .addClass('validation-rules-table__data-type')
            .text(this._optionText(this.fieldTypeInput, rule.fieldType))
        )
        .appendTo(row);

      $('<td>').text(this._displayValue(rule)).appendTo(row);
      $('<td>').text(rule.message || '-').appendTo(row);

      var actions = $('<td>').addClass('validation-rules-table__actions');

      $('<button>')
        .attr({
          type: 'button',
          'data-action': 'toggle',
          'data-rule-id': rule.id,
          title: rule.enabled ? this._text('disable-label') : this._text('enable-label')
        })
        .addClass('btn btn-link validation-rule-action validation-rule-action--toggle')
        .append($('<i>').addClass(rule.enabled ? 'fa fa-eye' : 'fa fa-eye-slash'))
        .appendTo(actions);

      $('<button>')
        .attr({
          type: 'button',
          'data-action': 'edit',
          'data-rule-id': rule.id,
          title: this._text('edit-label')
        })
        .addClass('btn btn-link validation-rule-action validation-rule-action--edit')
        .append($('<i>').addClass('fa fa-pencil'))
        .appendTo(actions);

      $('<button>')
        .attr({
          type: 'button',
          'data-action': 'delete',
          'data-rule-id': rule.id,
          title: this._text('delete-label')
        })
        .addClass('btn btn-link validation-rule-action validation-rule-action--delete')
        .append($('<i>').addClass('fa fa-trash'))
        .appendTo(actions);

      actions.appendTo(row);
      row.appendTo(this.ruleList);
    },

    _renderFieldList: function () {
      var names = [];
      this.fieldList.empty();

      this.schema.fields.forEach(function (field) {
        if (field.name && names.indexOf(field.name) === -1) {
          names.push(field.name);
        }
      });

      names.sort().forEach(function (name) {
        $('<option>').attr('value', name).appendTo(this.fieldList);
      }, this);
    },

    _displayValue: function (rule) {
      if (RULES[rule.constraint].valueType === 'boolean') {
        return '-';
      }

      if (Array.isArray(rule.value)) {
        return rule.value.join(', ');
      }

      return String(rule.value == null ? '' : rule.value) || '-';
    },

    _editRule: function (id) {
      var rule = this._findRule(id);
      if (!rule) {
        return;
      }

      this.ruleIdInput.val(rule.id);
      this.fieldInput.val(rule.field);
      this.fieldTypeInput.val(rule.fieldType);
      this.ruleTypeInput.val(rule.constraint);
      this.valueInput.val(this._displayValue(rule) === '-' ? '' : this._displayValue(rule));
      this.messageInput.val(rule.message || '');
      this.addButtonLabel.text(this._text('update-label'));
      this.cancelButton.removeClass('is-hidden');
      this._updateValueInput();
      this.fieldInput.trigger('focus');
    },

    _toggleRule: function (id) {
      var rule = this._findRule(id);
      if (!rule) {
        return;
      }

      rule.enabled = !rule.enabled;
      this._applyRulesToSchema();
      this._render();
    },

    _deleteRule: function (id) {
      this.rules = this.rules.filter(function (rule) {
        return rule.id !== id;
      });

      this._applyRulesToSchema();
      this._render();

      if (this.ruleIdInput.val() === id) {
        this._resetEditor();
      }
    },

    _findRule: function (id) {
      return this.rules.find(function (rule) {
        return rule.id === id;
      });
    },

    _selectExistingFieldType: function () {
      var name = $.trim(this.fieldInput.val());
      var field = this.schema.fields.find(function (item) {
        return item.name === name;
      });

      if (field && field.type) {
        this.fieldTypeInput.val(field.type);
      }
    },

    _updateValueInput: function () {
      var constraint = this.ruleTypeInput.val();
      var definition = RULES[constraint];
      var disabled = definition && definition.valueType === 'boolean';

      this.valueInput.prop('disabled', disabled);

      if (disabled) {
        this.valueInput.val('').attr('placeholder', '-');
      } else if (constraint === 'enum') {
        this.valueInput.attr('placeholder', 'AR, BR, PY');
      } else if (constraint === 'pattern') {
        this.valueInput.attr('placeholder', '^[A-Z]{2}$');
      } else {
        this.valueInput.attr('placeholder', this.defaultValuePlaceholder);
      }
    },

    _resetEditor: function () {
      this.ruleIdInput.val('');
      this.fieldInput.val('');
      this.fieldTypeInput.val('string');
      this.ruleTypeInput.val('required');
      this.valueInput.val('');
      this.messageInput.val('');
      this.addButtonLabel.text(this._text('add-label'));
      this.cancelButton.addClass('is-hidden');
      this._hideError();
      this._updateValueInput();
    },

    _showError: function (message) {
      this.errorBox.text(message).removeClass('is-hidden');
    },

    _hideError: function () {
      this.errorBox.text('').addClass('is-hidden');
    },

    _optionText: function (select, value) {
      var option = select.find('option[value="' + value + '"]');
      return option.length ? option.text() : value;
    },

    _text: function (name) {
      return this.el.attr('data-' + name) || '';
    },

    _newId: function () {
      return 'rule-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    }
  };
});

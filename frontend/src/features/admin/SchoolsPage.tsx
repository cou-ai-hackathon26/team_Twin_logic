import { Building2, MapPin, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { api } from '@/api/client'
import { useMe } from '@/api/hooks'
import { SCHOOLS_KEY, useSchools, type SchoolRow } from './schools'
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, Input, Label, Modal, PageHeader, PageLoader, Select } from '@/components/ui/primitives'

type SchoolForm = { name: string; upazila: string; district: string }

/** Admin only: schools above teachers, so a whole upazila or district can be summarised (counts only). */
export function SchoolsPage() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const list = useSchools(me?.role === 'admin')
  const refresh = () => {
    qc.invalidateQueries({ queryKey: SCHOOLS_KEY })
    qc.invalidateQueries({ queryKey: ['admin', 'teachers'] })
  }
  const create = useMutation({
    mutationFn: (b: SchoolForm) => api.post<SchoolRow>('/admin/schools', b),
    onSuccess: refresh,
  })
  const update = useMutation({
    mutationFn: (b: SchoolForm & { id: number }) => api.put<SchoolRow>(`/admin/schools/${b.id}`, b),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/admin/schools/${id}`),
    onSuccess: refresh,
  })
  const place = useMutation({
    mutationFn: (b: { cid: number; school_id: number | null }) => api.put(`/admin/classrooms/${b.cid}/school`, { school_id: b.school_id }),
    onSuccess: refresh,
  })

  const [form, setForm] = useState<SchoolForm>({
    name: '',
    upazila: '',
    district: '',
  })
  const [edit, setEdit] = useState<(SchoolForm & { id: number }) | null>(null)
  const [removeFor, setRemoveFor] = useState<SchoolRow | null>(null)

  if (me && me.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (list.isLoading) return <PageLoader />
  const schools = list.data?.schools ?? []
  const unassigned = list.data?.unassigned_classes ?? []

  return (
    <>
      <PageHeader
        title="Schools"
        subtitle="Group classes by school, upazila and district. A district officer then sees counts per school, never children."
        actions={
          <Link to="/district">
            <Button variant="secondary">
              <MapPin className="size-4" /> District view
            </Button>
          </Link>
        }
      />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Schools" subtitle="Teachers are placed in a school on the Teachers page; their own classes follow them." />
            <ErrorBox error={list.error ?? remove.error} className="mx-5 mt-3" />
            {!schools.length ? (
              <EmptyState icon={<Building2 className="size-6" />} title="No schools yet">
                Add the first school on the right.
              </EmptyState>
            ) : (
              <ul className="divide-y divide-slate-100">
                {schools.map((s) => (
                  <li key={s.id} className="flex flex-wrap items-start gap-x-4 gap-y-2 px-5 py-4">
                    <div className="grid size-10 place-items-center rounded-xl bg-teal-50 text-teal-800">
                      <Building2 className="size-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-ink">{s.name}</div>
                      <div className="text-xs text-slate-500">
                        {[s.upazila, s.district].filter(Boolean).join(' · ') || 'No upazila or district set'} · {s.teachers} teacher
                        {s.teachers === 1 ? '' : 's'} · {s.children} children
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {s.classes.length ? (
                          s.classes.map((c) => (
                            <Badge key={c.id} className="bg-slate-50 text-slate-700 ring-slate-200">
                              {c.name}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400">No classes yet</span>
                        )}
                      </div>
                    </div>
                    <span className="flex gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          setEdit({
                            id: s.id,
                            name: s.name,
                            upazila: s.upazila ?? '',
                            district: s.district ?? '',
                          })
                        }
                      >
                        <Pencil className="size-3.5" /> Edit
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setRemoveFor(s)} aria-label={`Remove ${s.name}`}>
                        <Trash2 className="size-4" />
                      </Button>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Classes without a school"
              subtitle="Shared classes and classes of teachers not yet in a school. They are left out of the district view until placed."
            />
            <ErrorBox error={place.error} className="mx-5 mt-3" />
            {!unassigned.length ? (
              <p className="px-5 py-4 text-sm text-slate-500">Every class belongs to a school.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {unassigned.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                    <span className="flex-1 font-medium text-ink">{c.name}</span>
                    <Select
                      className="w-56"
                      aria-label={`School for ${c.name}`}
                      value=""
                      disabled={!schools.length}
                      onChange={(e) =>
                        e.target.value &&
                        place.mutate({
                          cid: c.id,
                          school_id: Number(e.target.value),
                        })
                      }
                    >
                      <option value="">Place in a school…</option>
                      {schools.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </Select>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card className="h-fit">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Plus className="size-4 text-teal-700" /> Add a school
              </span>
            }
          />
          <form
            className="space-y-3 p-5"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate(form, {
                onSuccess: () => setForm({ name: '', upazila: '', district: '' }),
              })
            }}
          >
            <SchoolFields value={form} onChange={setForm} idPrefix="new" />
            <Button type="submit" disabled={form.name.trim().length < 2} loading={create.isPending}>
              <Plus className="size-4" /> Add school
            </Button>
            {create.isSuccess && <p className="text-sm text-teal-700">Added. Now place teachers in it on the Teachers page.</p>}
            <ErrorBox error={create.error} />
          </form>
        </Card>
      </div>

      <Modal
        open={!!edit}
        onClose={() => setEdit(null)}
        title="Edit school"
        footer={
          <>
            <Button variant="ghost" onClick={() => setEdit(null)}>
              Cancel
            </Button>
            <Button
              disabled={!edit || edit.name.trim().length < 2}
              loading={update.isPending}
              onClick={() => edit && update.mutate(edit, { onSuccess: () => setEdit(null) })}
            >
              Save
            </Button>
          </>
        }
      >
        {edit && <SchoolFields value={edit} onChange={(v) => setEdit({ ...edit, ...v })} idPrefix="edit" />}
        <ErrorBox error={update.error} className="mt-2" />
      </Modal>

      <Modal
        open={!!removeFor}
        onClose={() => setRemoveFor(null)}
        title={`Remove ${removeFor?.name ?? ''}?`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setRemoveFor(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                removeFor &&
                remove.mutate(removeFor.id, {
                  onSuccess: () => setRemoveFor(null),
                })
              }
            >
              Remove school
            </Button>
          </>
        }
      >
        Only the school is removed. Its {removeFor?.classes.length ?? 0} class(es), teachers, children and readings stay, without a school.
      </Modal>
    </>
  )
}

function SchoolFields({ value, onChange, idPrefix }: { value: SchoolForm; onChange: (v: SchoolForm) => void; idPrefix: string }) {
  return (
    <div className="space-y-3">
      <div>
        <Label htmlFor={`${idPrefix}-name`}>School name</Label>
        <Input id={`${idPrefix}-name`} value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor={`${idPrefix}-upazila`}>Upazila</Label>
          <Input id={`${idPrefix}-upazila`} value={value.upazila} onChange={(e) => onChange({ ...value, upazila: e.target.value })} />
        </div>
        <div>
          <Label htmlFor={`${idPrefix}-district`}>District</Label>
          <Input id={`${idPrefix}-district`} value={value.district} onChange={(e) => onChange({ ...value, district: e.target.value })} />
        </div>
      </div>
    </div>
  )
}
